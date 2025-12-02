# TOS_RTD Bridge
## Thinkorswim RTD → Redis for Thor (No Excel)

### Overview

This app is a **standalone RTD bridge**:

> **Thinkorswim RTD Server → C# RTD Client → Redis → Thor**

- No Excel
- No VBA
- No Office automation
- Safe to run on a PC that has Microsoft 365 installed
- Uses the same RTD interface Excel uses (`IRtdServer` / `IRTDUpdateEvent`),  
  but we talk to TOS directly instead of going through Excel.

---

## RTD Formulas Used in Excel Today

Current Excel formulas (examples):

```excel
=RTD("tos.rtd","","CLOSE","/YM:XCBT")
=RTD("tos.rtd","","OPEN","/YM:XCBT")
=RTD("tos.rtd","","NET_CHANGE","/YM:XCBT")
=RTD("tos.rtd","","HIGH","/YM:XCBT")
=RTD("tos.rtd","","LOW","/YM:XCBT")
=RTD("tos.rtd","","VOLUME","/YM:XCBT")
=RTD("tos.rtd","","BID","/YM:XCBT")
=RTD("tos.rtd","","LAST","/YM:XCBT")
=RTD("tos.rtd","","ASK","/YM:XCBT")
=RTD("tos.rtd","","BID_SIZE","/YM:XCBT")
=RTD("tos.rtd","","ASK_SIZE","/YM:XCBT")


We will subscribe to all of these directly from C#, and push them into Redis.

### Requirements

- Windows PC with Thinkorswim installed, logged in, and running
- .NET 8 SDK (6 also works, but instructions assume 8)
- Visual Studio Code
- Docker container `thor_redis` exposing Redis on `0.0.0.0:6379 -> 6379/tcp`

With that mapping, the bridge can always connect via `localhost:6379`.

### Project Setup (VS Code + dotnet)

Run the following from PowerShell:

```powershell
cd A:\Thor
dotnet new console -n TosRtdBridge -f net8.0-windows
cd TosRtdBridge
dotnet add package Microsoft.Office.Interop.Excel
dotnet add package StackExchange.Redis
code .
```

That scaffolds the console app, installs the only two dependencies, and opens the folder in VS Code.

### Core Concept

We create an instance of the TOS RTD server using its ProgID: "tos.rtd".

We implement Excel.IRTDUpdateEvent so TOS can call us back.

We call ConnectData for each topic (CLOSE, OPEN, etc.).

Whenever TOS has new data, it calls UpdateNotify() on us.

Inside UpdateNotify, we call RefreshData and write the new values into Redis.

## Implementation

### `TosRtdClient.cs`

Create `TosRtdClient.cs` and add:

using System;
using System.Collections.Generic;
using Excel = Microsoft.Office.Interop.Excel;
using StackExchange.Redis;

namespace TosRtdBridge
{
    /// <summary>
    /// RTD client that connects directly to Thinkorswim's RTD server (tos.rtd)
    /// and forwards all updates into Redis.
    /// </summary>
    public class TosRtdClient : Excel.IRTDUpdateEvent
    {
        private readonly Excel.IRtdServer _server;
        private readonly ConnectionMultiplexer _redis;
        private readonly IDatabase _db;

        // topicID -> Redis key
        private readonly Dictionary<int, string> _topicKeys = new();
        private int _nextTopicId = 1;

        public TosRtdClient(string tosProgId, string redisConnectionString)
        {
            // 1. Connect to Redis
            _redis = ConnectionMultiplexer.Connect(redisConnectionString);
            _db = _redis.GetDatabase();

            // 2. Create RTD COM server for Thinkorswim
            var type = Type.GetTypeFromProgID(tosProgId);
            if (type == null)
            {
                throw new InvalidOperationException(
                    $"Could not find TOS RTD ProgID '{tosProgId}'. Is Thinkorswim RTD installed?");
            }

            _server = (Excel.IRtdServer)Activator.CreateInstance(type)!;

            // 3. Register this object as the RTD callback
            int result = _server.ServerStart(this);
            Console.WriteLine($"[TOS RTD] ServerStart result = {result}");
        }

        /// <summary>
        /// Subscribe to a single RTD topic.
        /// </summary>
        /// <param name="redisKey">Key to write into Redis (e.g. RTD:YM:LAST)</param>
        /// <param name="topicArgs">The RTD arguments after ProgID/Server, e.g. "LAST", "/YM:XCBT"</param>
        public int Subscribe(string redisKey, params string[] topicArgs)
        {
            int topicId = _nextTopicId++;

            _topicKeys[topicId] = redisKey;

            Array args = topicArgs;
            bool getNewValues = false;

            object initial = _server.ConnectData(topicId, ref args, ref getNewValues);

            Console.WriteLine($"[TOS RTD] SUBSCRIBE TopicID={topicId}, Key={redisKey}, Initial={initial}");
            if (initial != null)
            {
                _db.StringSet(redisKey, initial.ToString());
            }

            return topicId;
        }

        /// <summary>
        /// Called by the RTD server when new data is available.
        /// </summary>
        public void UpdateNotify()
        {
            int topicCount = 0;
            Array data = _server.RefreshData(ref topicCount);

            for (int i = 0; i < topicCount; i++)
            {
                int topicId = (int)data.GetValue(0, i);
                object value = data.GetValue(1, i);

                if (_topicKeys.TryGetValue(topicId, out string redisKey))
                {
                    Console.WriteLine($"[TOS RTD] UPDATE {redisKey} = {value}");
                    _db.StringSet(redisKey, value?.ToString());
                }
            }
        }

        /// <summary>
        /// Desired heartbeat interval in milliseconds. TOS may or may not use this.
        /// </summary>
        public int HeartbeatInterval { get; set; } = 1000;

        /// <summary>
        /// Called when Excel (or RTD host) is shutting down. For us this is just a log hook.
        /// </summary>
        public void Disconnect()
        {
            Console.WriteLine("[TOS RTD] Disconnect() called on callback.");
            _server.ServerTerminate();
        }

        /// <summary>
        /// Manual shutdown from our app.
        /// </summary>
        public void Shutdown()
        {
            Console.WriteLine("[TOS RTD] Manual shutdown.");
            _server.ServerTerminate();
            _redis.Dispose();
        }
    }
}

### `Program.cs`

using System;

namespace TosRtdBridge
{
    class Program
    {
        // The TOS RTD ProgID. This matches the first string in your Excel RTD formulas.
        private const string TosProgId = "tos.rtd";

        // Redis connection string (from Docker port mapping 0.0.0.0:6379->6379/tcp).
        private const string RedisConnection = "localhost:6379";

        static void Main(string[] args)
        {
            Console.WriteLine("Starting TOS RTD → Redis bridge...");
            var client = new TosRtdClient(TosProgId, RedisConnection);

            SubscribeAllSymbols(client);

            Console.WriteLine("Bridge running. Press ENTER to exit.");
            Console.ReadLine();

            client.Shutdown();
        }

        /// <summary>
        /// Subscribe all futures/index contracts and fields that currently exist in the Excel sheet.
        /// </summary>
        private static void SubscribeAllSymbols(TosRtdClient client)
        {
            // YM  (E-mini Dow Jones, /YM:XCBT)
            SubscribeSymbol(client, "YM", "/YM:XCBT");

            // ES  (E-mini S&P 500, /ES:XCME)
            SubscribeSymbol(client, "ES", "/ES:XCME");

            // NQ  (E-mini Nasdaq 100, /NQ:XCME)
            SubscribeSymbol(client, "NQ", "/NQ:XCME");

            // RTY (Russell, /RTY:XCME)
            SubscribeSymbol(client, "RTY", "/RTY:XCME");

            // CL  (Crude Oil, /CL:XNYM)
            SubscribeSymbol(client, "CL", "/CL:XNYM");

            // SI  (Silver, /SI:XCEC)
            SubscribeSymbol(client, "SI", "/SI:XCEC");

            // HG  (Copper, /HG:XCEC)
            SubscribeSymbol(client, "HG", "/HG:XCEC");

            // GC  (Gold, /GC:XCEC)
            SubscribeSymbol(client, "GC", "/GC:XCEC");

            // VX  (VIX futures, /VX:XCBF)
            SubscribeSymbol(client, "VX", "/VX:XCBF");

            // DXY (Dollar Index, uses "$DXY" instead of /SYM:EXCH)
            SubscribeSymbol(client, "DXY", "$DXY");

            // ZB  (30-Year Bond, /ZB:XCBT)
            SubscribeSymbol(client, "ZB", "/ZB:XCBT");
        }

        /// <summary>
        /// Helper to subscribe the standard 11 fields for a single symbol.
        /// Keys in Redis: RTD:{symbol}:{FIELD}, e.g. RTD:YM:LAST
        /// </summary>
        private static void SubscribeSymbol(TosRtdClient client, string symbol, string tosInstrument)
        {
            void Sub(string field) =>
                client.Subscribe($"RTD:{symbol}:{field}", field, tosInstrument);

            Sub("CLOSE");
            Sub("OPEN");
            Sub("NET_CHANGE");
            Sub("HIGH");
            Sub("LOW");
            Sub("VOLUME");
            Sub("BID");
            Sub("LAST");
            Sub("ASK");
            Sub("BID_SIZE");
            Sub("ASK_SIZE");
        }
    }
}


## Running the Bridge

1. Launch Thinkorswim and log in so RTD is live.
2. Confirm the `thor_redis` container is running (port 6379 exposed to localhost).
3. From `TosRtdBridge/`, run:

```powershell
dotnet run
```

You should then see logs like:

Starting TOS RTD → Redis bridge...
[TOS RTD] ServerStart result = 1
[TOS RTD] SUBSCRIBE TopicID=1, Key=RTD:YM:CLOSE, Initial=...
...
[TOS RTD] UPDATE RTD:YM:LAST = 39251
[TOS RTD] UPDATE RTD:ES:LAST = 5190.25
...

Check Redis from another terminal:

redis-cli -h localhost -p 6379
GET RTD:YM:LAST
GET RTD:ES:LAST
GET RTD:NQ:VOLUME


## Production Hardening

To keep the bridge running as a background service:

- Convert the console app to a Worker Service or wrap it with a Windows Scheduled Task/service runner.
- Swap `Console.WriteLine` for structured logging (Serilog, NLog, etc.).
- Move configuration (symbols, Redis connection, heartbeat) into `appsettings.json`.
- Keep the Redis key format (`RTD:{symbol}:{field}`) stable so Thor can consume the same keys (`RTD:YM:LAST`, `RTD:ES:LAST`, etc.).
- Auto-start the bridge at login so data flows as soon as Thinkorswim is ready.

Safety Notes

We do not register any COM servers.

We do not override Excel.Application or any Office ProgIDs.

This app is just a COM client for tos.rtd, so it cannot break Office.

It’s safe to run alongside Excel, Office 365, and other COM-based apps.


---

If you want, next step I can help you:

- Adjust the Redis key pattern to match your existing Thor models, and  
- Sketch how the Django backend should read from `RTD:{symbol}:{field}` and store snapshots at market close.

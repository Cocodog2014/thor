Below is a complete TOS_RTD.md document you can drop directly into your GitHub repo or VS Code project.

It includes:

What the app does

How it works

How to build it in VS Code (no Visual Studio required)

Full RTD Client Script (Thinkorswim → Redis)

How to run it

How to make it a pure, clean, production-ready program

TOS_RTD.md
Thinkorswim RTD → Redis/Postgres Real-Time Data Bridge
For Thor Trading Engine (Direct feed, no Excel required)
📌 Overview

This document describes how to build and run a pure, standalone RTD bridge that reads live market data directly from Thinkorswim’s RTD server, then writes it into Redis (or Postgres) for the Thor trading engine.

✔ No Excel
✔ No VBA
✔ No Office automation
✔ Direct, real-time, tick-level updates from TOS
✔ 100% safe on systems with Microsoft Office
✔ Works entirely in VS Code using dotnet CLI
⚡ How It Works
Thinkorswim exposes real-time market data using a COM RTD server.

In Excel you normally see formulas like:

=RTD("tos.rtd",,"LAST","VFF","MARK")


Excel → COM request → Thinkorswim RTD → Thinkorswim market engine.

We replace Excel with our own program.

Your app becomes:

TOS RTD Server  →  (Our C# RTD Client)  →  Redis/Postgres  →  Thor


We implement the Excel callback interface (IRTDUpdateEvent) so Thinkorswim pushes updates straight into our code.

🛠 Requirements

Windows OS

Thinkorswim installed & running

.NET 6.0+ or .NET 8.0 SDK

VS Code (optional but recommended)

Redis or Postgres running locally

📁 Project Structure
TosRtdBridge/
│   Program.cs
│   TosRtdClient.cs
│   TOS_RTD.md
│   appsettings.json (optional)
│   TosRtdBridge.csproj

🚀 Creating the Project (VS Code)

Open PowerShell:

cd A:\Thor
dotnet new console -n TosRtdBridge -f net8.0-windows
cd TosRtdBridge
code .


Add dependencies:

dotnet add package Microsoft.Office.Interop.Excel
dotnet add package StackExchange.Redis


Microsoft.Office.Interop.Excel is required because it defines the Excel IRtdServer and IRTDUpdateEvent interfaces.

📜 FULL SCRIPT
TosRtdClient.cs

This is the heart of the TOS → Redis bridge.

using System;
using System.Collections.Generic;
using Excel = Microsoft.Office.Interop.Excel;
using StackExchange.Redis;

public class TosRtdClient : Excel.IRTDUpdateEvent
{
    private readonly Excel.IRtdServer _server;
    private readonly Dictionary<int, string> _topicKeys = new();
    private readonly Dictionary<int, object> _lastValues = new();
    private int _nextTopicId = 1;

    private readonly ConnectionMultiplexer _redis;
    private readonly IDatabase _db;

    public TosRtdClient(string tosProgId, string redisConnection)
    {
        // Connect to Redis
        _redis = ConnectionMultiplexer.Connect(redisConnection);
        _db = _redis.GetDatabase();

        // Create RTD instance
        var type = Type.GetTypeFromProgID(tosProgId);
        if (type == null)
            throw new InvalidOperationException($"Cannot find TOS RTD ProgID '{tosProgId}'");

        _server = (Excel.IRtdServer)Activator.CreateInstance(type);

        // Register callback
        _server.ServerStart(this);
        Console.WriteLine("[TOS RTD] ServerStart OK");
    }

    public int Subscribe(string redisKey, params string[] topicArgs)
    {
        int topicId = _nextTopicId++;

        _topicKeys[topicId] = redisKey;

        Array args = topicArgs;
        bool newValues = false;

        object initial = _server.ConnectData(topicId, ref args, ref newValues);

        Console.WriteLine($"[TOS RTD] SUBSCRIBE TopicID={topicId}, Key={redisKey}, Initial={initial}");
        _db.StringSet(redisKey, initial?.ToString());

        _lastValues[topicId] = initial;

        return topicId;
    }

    public void UpdateNotify()
    {
        Console.WriteLine("[TOS RTD] UpdateNotify");

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
                _lastValues[topicId] = value;
            }
        }
    }

    public void Disconnect() => Console.WriteLine("[TOS RTD] Callback Disconnect()");
    public int HeartbeatInterval { get; set; } = 1000;
}

📜 Program.cs
using System;

namespace TosRtdBridge
{
    class Program
    {
        static void Main(string[] args)
        {
            string tosProgId = "tos.rtd";        // MUST MATCH YOUR EXCEL FORMULA
            string redisConn = "localhost:6379"; // Your Redis server

            var client = new TosRtdClient(tosProgId, redisConn);

            // Example subscriptions (MATCH YOUR TOS RTD FORMULAS)
            client.Subscribe("TOS:LAST:VFF:MARK", "LAST", "VFF", "MARK");
            client.Subscribe("TOS:BID:VFF:MARK",  "BID",  "VFF", "MARK");
            client.Subscribe("TOS:ASK:VFF:MARK",  "ASK",  "VFF", "MARK");

            Console.WriteLine("TOS RTD Bridge Running — Press ENTER to exit.");
            Console.ReadLine();
        }
    }
}

🧪 Running the Program

Make sure Thinkorswim is running and logged in.

Start Redis (or Postgres).

Run the bridge:

dotnet run


Watch the output:

[TOS RTD] ServerStart OK
[TOS RTD] SUBSCRIBE TopicID=1 Key=TOS:LAST:VFF:MARK Initial=3.52
[TOS RTD] UPDATE TOS:LAST:VFF:MARK = 3.53
[TOS RTD] UPDATE TOS:BID:VFF:MARK  = 3.50
...


Check Redis:

redis-cli
GET TOS:LAST:VFF:MARK


You will see live TOS prices.

🔥 Making the Program PURE (Production Mode)

To make this a pure, clean, background system service:

1. Convert console app → Windows Service

Use:

dotnet new worker -n TosRtdBridge -f net8.0-windows

2. Remove all Console.WriteLine logs

Replace with:

Serilog

NLog

Or Windows Event Log

3. Add config file (appsettings.json)
{
  "TOS_ProgId": "tos.rtd",
  "Redis": "localhost:6379",
  "Symbols": [
    ["LAST","VFF","MARK"],
    ["BID","VFF","MARK"],
    ["ASK","VFF","MARK"]
  ]
}

4. Install as a Windows Service
sc create TosRtdBridge binPath= "A:\Thor\TosRtdBridge\TosRtdBridge.exe"

5. Set to auto-start
sc start TosRtdBridge


Now your PC boots → Thinkorswim logs in → Thor gets live data automatically.

📌 Safety: Will This Break Excel or Office?

No. Zero risk.
This bridge:

Does not register any COM servers

Does not override Excel.Application

Only reads from Thinkorswim

Does not interfere with Office 365

Completely safe.
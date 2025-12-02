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
        /// Called if the RTD server thread is being terminated.
        /// </summary>
        public void ThreadTerminate()
        {
            Console.WriteLine("[TOS RTD] ThreadTerminate() called.");
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

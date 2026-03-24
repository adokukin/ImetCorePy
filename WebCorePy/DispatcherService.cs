using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace WebCorePy
{
    public class FileUploadModel
    {
        public string filename { get; set; }
        public byte[] bytes { get; set; }
    }

    public class JobRequest
    {
        public int? slot { get; set; }
        public List<string> algorithms { get; set; }
        public int timeout { get; set; }
        public FileUploadModel fileTrain { get; set; }
        public FileUploadModel filePredict { get; set; }
    }

    public class DispatcherService : BackgroundService
    {
        public const int NumProcessors = 5;

        private Channel<Message> channel;
        private readonly ILogger logger;

        private PoolWorker[] pool;
        public DispatcherService(IChannelSingletonService channelService, ILogger<DispatcherService> logger)
        {
            channel = channelService.channel;
            this.logger = logger;

            pool = new PoolWorker[NumProcessors];
        }

        protected int GetFreeSlot()
        {
            int oldestProcessor = -1;
            DateTime minStarted = DateTime.MaxValue;

            for (int i = 0; i < pool.Length; i++)
            {
                DateTime? started = pool[i].start;
                if (started == null)
                {
                    return i + 1;
                }
                else
                {
                    if ((DateTime)started < minStarted)
                    {
                        minStarted = (DateTime)started;
                        oldestProcessor = i;
                    }
                }
            }
            return oldestProcessor;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            for (int i = 0; i < pool.Length; i++)
            {
                pool[i] = new PoolWorker(stoppingToken);
            }

            Message candidate;
            while (!stoppingToken.IsCancellationRequested)
            {
                bool available = await channel.Reader.WaitToReadAsync(stoppingToken);
                if (available && channel.Reader.CanPeek)
                {
                    if (channel.Reader.TryPeek(out candidate) && (candidate.target == 0))
                    {
                        Message request = await channel.Reader.ReadAsync();
                        logger.LogInformation($"Read success {request.id}, {request.source} -> {request.target}, {request.session}");

                        Message response = new Message();
                        response.id = request.id;
                        response.session = request.session;
                        response.source = 0;

                        int slot;
                        if (request.source == null)
                        {
                            slot = GetFreeSlot(); // TODO: should there be error?
                        }
                        else
                        {
                            slot = (int)request.source;
                        }
                        response.target = slot;

                        if (request.request == null)
                        {
                            throw new InvalidOperationException();
                        }
                        WorkerRequest workerRequest = (WorkerRequest)(request.request);
                        response.response = await pool[slot - 1].Command(workerRequest);

                        WorkerResponse workerResponse = (WorkerResponse)(response.response);
                        logger.LogInformation($"Processed {response.id}, {response.source} -> {response.target}, {workerResponse.state}");
                        channel.Writer.TryWrite(response);
                    }
                }
            }
        }
    }
}

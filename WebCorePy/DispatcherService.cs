using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace WebCorePy
{
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
            for (int i = 0; i < pool.Length; i++)
            {
                pool[i] = new PoolWorker();
            }
        }

        protected int GetFreeSlot()
        {
            int oldestProcessor = -1;
            DateTime minStarted = DateTime.MaxValue;

            for (int i = 0;i < pool.Length;i++)
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
            Message candidate;
            while (!stoppingToken.IsCancellationRequested)
            {
                bool available = await channel.Reader.WaitToReadAsync(stoppingToken);
                if (available && channel.Reader.CanPeek) {
                    if (channel.Reader.TryPeek(out candidate) && (candidate.target == 0))
                    {
                        Message request = await channel.Reader.ReadAsync();
                        logger.LogInformation($"Read success {request.id}, {request.source} -> {request.target}, {request.session}");

                        Message response;
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

                        switch (request.status) 
                        {
                            case Status.START:
                                // other clients can't obtain slot inbetween processing (EMPTY->BUSY), 
                                // but it still can change its state from BUSY to READY
                                lock (pool)
                                {
                                    if (pool[slot].state == WorkerState.EMPTY)
                                    {
                                        pool[slot].Start();
                                        response.status = Status.OK;
                                    }
                                    else
                                    {
                                        response.status = Status.BUSY;
                                    }
                                }
                                break;

                            case Status.CLEAR:
                                lock (pool)
                                {
                                    pool[slot].Cancel(); // TODO: is it ok to cancel running task?
                                    response.status = Status.OK;
                                }
                                break;

                            default:
                                switch (pool[slot - 1].State) // TODO: thread safety
                                {
                                    case WorkerState.BUSY:
                                        response.status = Status.BUSY;
                                        break;
                                    default:
                                        response.status = Status.READY;
                                        break;
                                }
                                break;
                        }


                        response.value = await pool[slot - 1].GetStatus();

                        channel.Writer.TryWrite(response);
                    }
                }
            }
        }
    }
}

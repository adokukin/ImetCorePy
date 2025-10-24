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
            DateTime? minStarted = DateTime.MaxValue;

            for (int i = 0;i < pool.Length;i++)
            {
                if (pool[i].state == WorkerState.EMPTY)
                {
                    return i;
                }
                else
                {
                    DateTime started = (DateTime)pool[i].start;
                    if (started < minStarted)
                    {
                        minStarted = started;
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
                        logger.LogInformation($"Read success {request.id}, {request.source} -> {request.target}, {request.session}, {request.value}");

                        Message response;
                        response.id = request.id;
                        response.session = request.session;
                        response.source = 0;

                        switch (request.status) 
                        {
                            case Status.NEW:
                                if (request.source == null)
                                {
                                    int slot = GetFreeSlot();
                                    response.target = slot;
                                    if (pool[slot].state == WorkerState.EMPTY)
                                    {
                                        // TODO: start task
                                        response.status = Status.ACCEPTED;
                                    }
                                    else
                                    {
                                        response.status = Status.BUSY;
                                    }
                                }
                                else
                                {
                                    int slot = (int)request.source;
                                    response.target = slot;
                                    switch (pool[slot].state)
                                    {
                                        case WorkerState.READY:
                                            response.status = Status.READY;
                                            break;
                                        case WorkerState.BUSY:
                                            response.status = Status.IN_PROGRESS;
                                            break;
                                        default:
                                            response.status = Status.ACCEPTED;
                                            break;
                                    }
                                }
                                response.value = "response";
                                break;
                            case Status.CHECK:
                                if (request.source == null)
                                {
                                    response.target = null;
                                    response.status = Status.ERROR;
                                }
                                else
                                {
                                    int slot = (int)request.source;
                                    response.target = slot;
                                    switch (pool[slot].state)
                                    {
                                        case WorkerState.READY:
                                            response.status = Status.READY;
                                            break;
                                        case WorkerState.BUSY:
                                            response.status = Status.IN_PROGRESS;
                                            break;
                                        default:
                                            response.status = Status.EMPTY;
                                            break;
                                    }
                                }
                                response.value = "response";
                                break;
                            case Status.CLEAR:
                                if (request.source == null)
                                {
                                    response.target = null;
                                    response.status = Status.ERROR;
                                }
                                else
                                {
                                    int slot = (int)request.source;
                                    response.target = slot;
                                    switch (pool[slot].state)
                                    {
                                        case WorkerState.READY:
                                            // TODO: delete files
                                            break;
                                        case WorkerState.BUSY:
                                            // TODO: stop calculation
                                            // TODO: delete files
                                            break;
                                        default:
                                            break;
                                    }
                                    response.status = Status.EMPTY;
                                }
                                response.value = "response";
                                break;
                            default:
                                response.target = request.source;
                                response.status = Status.ERROR;
                                response.value = "response";
                                break;
                        }

                        channel.Writer.TryWrite(response);
                    }
                }
            }
        }
    }
}

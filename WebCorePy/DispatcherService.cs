using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace WebCorePy
{
    public enum State
    {
        EMPTY,
        IN_PROGRESS,
        READY
    }

    public struct Processor
    {
        public string process; // TODO: proper type
        public State state;
        public DateTime? start;
        public DateTime? end;
        public string file_train;
        public string file_test;
        public Processor ()
        {
            process = null;
            state = State.EMPTY;
            start = null;
            end = null;
            file_train = null;
            file_test = null;
        }
    }

    public class DispatcherService : BackgroundService
    {
        public const int NumProcessors = 5;

        private Channel<Message> channel;
        private readonly ILogger logger;

        private Processor[] pool;
        public DispatcherService(IChannelSingletonService channelService, ILogger<DispatcherService> logger)
        {
            channel = channelService.channel;
            this.logger = logger;

            pool = new Processor[NumProcessors];
            for (int i = 0; i < pool.Length; i++)
            {
                pool[i] = new Processor();
            }
        }

        protected int GetFreeSlot()
        {
            int oldestProcessor = -1;
            DateTime? minStarted = DateTime.MaxValue;

            for (int i = 0;i < pool.Length;i++)
            {
                if (pool[i].state == State.EMPTY)
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

                        if (request.status == Status.NEW)
                        {
                            if (request.source == null)
                            {
                                int slot = GetFreeSlot();
                                response.target = slot;
                                response.status = pool[slot].state == State.EMPTY ? Status.ACCEPTED : Status.BUSY;
                            }
                            else
                            {
                                int slot = (int)request.source;
                                response.target = slot;
                                switch(pool[slot].state)
                                {
                                    case State.READY:
                                        response.status = Status.READY;
                                        break;
                                    case State.IN_PROGRESS:
                                        response.status = Status.IN_PROGRESS;
                                        break;
                                    default:
                                        response.status = Status.ACCEPTED;
                                        break;
                                }
                            }
                            response.value = "response";
                        }
                        else if (request.status == Status.CHECK) 
                        {
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
                                    case State.READY:
                                        response.status = Status.READY;
                                        break;
                                    case State.IN_PROGRESS:
                                        response.status = Status.IN_PROGRESS;
                                        break;
                                    default:
                                        response.status = Status.EMPTY;
                                        break;
                                }
                            }
                            response.value = "response";
                        }
                        else
                        {
                            response.target = request.source;
                            response.status = Status.ERROR;
                            response.value = "response";
                        }

                        channel.Writer.TryWrite(response);
                    }
                }
            }
        }
    }
}

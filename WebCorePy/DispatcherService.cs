using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace WebCorePy
{
    public struct Processor
    {
        public string process; // TODO: proper type
        // TODO: file references
    }

    public class DispatcherService : BackgroundService
    {
        public const int NumProcessors = 5;

        private Channel<Message> channel;
        private readonly ILogger logger;

        private Processor?[] pool;
        public DispatcherService(IChannelSingletonService channelService, ILogger<DispatcherService> logger)
        {
            channel = channelService.channel;
            this.logger = logger;

            pool = new Processor?[NumProcessors];
            for (int i = 0; i < pool.Length; i++)
            {
                pool[i] = null;
            }
        }

        protected int? GetFreeSlot()
        {
            int? ret = null;
            for (int i = 0;i < pool.Length;i++)
            {
                if (pool[i] == null)
                {
                    pool[i] = new Processor();
                    ret = i;
                    break;
                }
            }
            return ret;
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
                        if (request.source == null)
                        {
                            int? slot = GetFreeSlot();
                            if (slot != null)
                            {
                                response.target = (int)slot;
                                response.status = Status.SUCCESS;
                            }
                            else
                            {
                                response.target = null;
                                response.status = Status.ERROR;
                            }
                        }
                        else
                        {
                            response.target = (int)request.source;
                            response.status = Status.SUCCESS;
                        }
                        response.value = "response";
                        channel.Writer.TryWrite(response);
                    }
                }
            }
        }
    }
}

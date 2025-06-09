using Microsoft.Extensions.Hosting;
using System;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace WebCorePy
{
    public class DispatcherService : BackgroundService
    {
        private Channel<Message> channel;
        public DispatcherService(IChannelSingletonService channelService)
        {
            channel = channelService.channel;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            Message candidate;
            while (!stoppingToken.IsCancellationRequested)
            {
                await channel.Reader.WaitToReadAsync(stoppingToken);
                if (channel.Reader.CanPeek) {
                    channel.Reader.TryPeek(out candidate);
                    if (candidate.target == 0)
                    {
                        Message request;
                        channel.Reader.TryRead(out request);
                        
                        Message response;
                        response.id = request.id;
                        response.session = request.session;
                        response.source = 0;
                        // TODO: assign new instead of 1
                        response.target = request.source != null ? (int)request.source : 1;
                        response.value = "response";
                        channel.Writer.TryWrite(response);
                    }
                }
            }
        }
    }
}

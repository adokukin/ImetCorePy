using Microsoft.Extensions.Hosting;
using System;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace WebCorePy
{
    public class DispatcherService : BackgroundService
    {
        IChannelSingletonService channel { get; }
        public DispatcherService(IChannelSingletonService channel)
        {
            this.channel = channel;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                }
                catch (Exception ex)
                {
                    // обработка ошибки однократного неуспешного выполнения фоновой задачи
                }

                await Task.Delay(5000);
            }
        }
    }
}

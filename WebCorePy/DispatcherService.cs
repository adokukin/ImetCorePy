using Microsoft.Extensions.Hosting;
using System.Threading;
using System.Threading.Tasks;

namespace WebCorePy
{
    public class DispatcherService : BackgroundService
    {
        protected override Task ExecuteAsync(CancellationToken stoppingToken)
        {
            throw new System.NotImplementedException();
        }
    }
}

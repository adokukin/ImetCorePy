using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using System;
using System.Diagnostics;
using System.IO;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Threading.Channels;
using System.Threading.Tasks;
using WebCorePy.Models;

namespace WebCorePy.Controllers
{
    public class HomeController : Controller
    {
        IWebHostEnvironment env { get; }
        IConfiguration config { get; }
        Channel<Message> channel {  get; }
        public HomeController(IWebHostEnvironment env, IConfiguration config, IChannelSingletonService channelService) {
            this.env = env;
            this.config = config;
            this.channel = channelService.channel;
        }

        public IActionResult Index()
        {
            return View();
        }

        public IActionResult Privacy()
        {
            return View();
        }

        public IActionResult Format()
        {
            return View();
        }

        [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
        public IActionResult Error()
        {
            return View(new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier });
        }

        private JsonResult DispatcherResponceToJson(Message response)
        {
            String msg = $"<div class=\"alert alert-warning\" role=\"alert\">Проверка обработчика {response.target} для {HttpContext.Session.Id}, id {response.id}, ---</div>";
            WorkerResult? result = null;
            WorkerState? state = null;
            Decimal progress = 0;
            string[] output = [];
            int? slot = response.target;

            if (response.response != null)
            {
                WorkerResponse workerResponse = (WorkerResponse)(response.response);
                msg = $"<div class=\"alert alert-primary\" role=\"alert\">Проверка обработчика {response.target} для {HttpContext.Session.Id}, id {response.id}, state {workerResponse.state}</div>";
                result = workerResponse.result;
                state = workerResponse.state;
                progress = workerResponse.progress;
                output = workerResponse.output;
            }

            return Json(new { result = result, state = state, message = msg, progress = progress, output = output, slot = slot });
        }

        private async ValueTask<Message> RequestDispatcher(int? slot, WorkerRequest data)
        {
            Message candidate;
            Message response = new Message();

            Message request = new Message();

            int? id = HttpContext.Session.GetInt32("id");
            request.id = id == null ? 1 : (int)id + 1;
            HttpContext.Session.SetInt32("id", request.id);

            request.source = slot;

            request.session = HttpContext.Session.Id;
            request.target = 0;
            request.request = data;

            channel.Writer.TryWrite(request);

            bool responded = false;
            while (!responded)
            {
                // TODO: cancellation condition
                bool available = await channel.Reader.WaitToReadAsync();

                if (available && channel.Reader.CanPeek)
                {
                    if (channel.Reader.TryPeek(out candidate))
                    {
                        if ((candidate.target != 0) &&
                            ((candidate.session == request.session) || (candidate.target == request.source)))
                        {
                            response = await channel.Reader.ReadAsync();

                            if (response.id == request.id)
                            {
                                if ((slot != null) && ((int)slot != response.target))
                                {
                                    // TODO: deal with error
                                    Console.WriteLine(@"Error: wrong response target {response.target} instead of {slot}");
                                }
                                responded = true;
                            }
                            else
                            {
                                // TODO: deal with possible errors
                            }
                        }
                    }
                }
            }

            return response;
        }

        [HttpGet("JobStatus")]
        public async Task<IActionResult> Get(int? slot)
        {
            Message response = await RequestDispatcher(slot, new WorkerRequest(WorkerCommand.CHECK));
            return DispatcherResponceToJson(response);
        }

        private string SaveUploadedFile(string uploadDirectory, string stage, FileUploadModel uploaded)
        {
            string filePath = null;

            if ((uploaded != null) && (uploaded.filename != null))
            {
                var safeFileName = stage + Path.GetExtension(uploaded.filename);
                filePath = Path.Combine(uploadDirectory, safeFileName);
                System.IO.File.WriteAllBytes(filePath, uploaded.bytes);
            }

            return filePath;
        }

        private (string, string) SaveJobData(int slot, JobRequest request)
        {
            string uploadDirectory = Path.Combine(Directory.GetCurrentDirectory(), "Data" + slot.ToString());
            DirectoryInfo di = new DirectoryInfo(uploadDirectory);
            foreach (FileInfo f in di.EnumerateFiles())
            {
                f.Delete();
            }

            var train = SaveUploadedFile(uploadDirectory, "training", request.fileTrain);
            var predict = SaveUploadedFile(uploadDirectory, "predicting", request.filePredict);

            var filePath = Path.Combine(uploadDirectory, "metadata.json");
            var options = new JsonSerializerOptions { 
                WriteIndented = true, 
                Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping 
            };
            // TODO: filter relevant fields
            System.IO.File.WriteAllText(filePath, JsonSerializer.Serialize(request, options));

            return (train, predict);
        }

        [HttpPost("JobStart")]
        public async Task<IActionResult> Post([FromBody] JobRequest request)
        {
            if (request.slot != null)
            {
                var slot = (int)request.slot;
                (var train, var predict) = SaveJobData(slot, request);

                WorkerRequest workerRequest = new WorkerRequest(
                    WorkerCommand.START,
                    train,
                    predict,
                    request.algorithms,
                    request.timeout,
                    request.folds
                );
                Message response = await RequestDispatcher(slot, workerRequest);
                return DispatcherResponceToJson(response);
            }
            else
            {
                return null;
            }
        }
    }
}

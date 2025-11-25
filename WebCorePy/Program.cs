using System;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using WebCorePy;

var builder = WebApplication.CreateBuilder(args);
builder.Services.Configure<CookiePolicyOptions>(options =>
{
    // This lambda determines whether user consent for non-essential cookies is needed for a given request.
    options.CheckConsentNeeded = context => true;
});

builder.Logging.AddDebug();

builder.Services.AddSingleton<IHttpContextAccessor, HttpContextAccessor>(); // добавим возможность доступа к контексту HttpContext
builder.Services.AddSingleton<IChannelSingletonService, ChannelSingletonService>();
builder.Services.AddHostedService<WebCorePy.DispatcherService>();
builder.Services.AddDistributedMemoryCache();
builder.Services.AddSession(options =>
{
    // TODO: reconsider timeout scenario
    options.IdleTimeout = TimeSpan.FromMinutes(60);
    options.Cookie.HttpOnly = true;
    options.Cookie.IsEssential = true;
});

builder.Services.AddControllersWithViews()
    .AddNewtonsoftJson();
builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor();

var app = builder.Build();
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}
else
{
    app.UseExceptionHandler("/Home/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();

app.UseCookiePolicy();
app.UseSession();
app.UseRouting();

app.UseAuthorization();

app.MapControllerRoute(
        name: "default",
        pattern: "{controller=Home}/{action=Index}/{id?}"
);
app.MapRazorPages();
app.MapBlazorHub();

System.Text.Encoding.RegisterProvider(System.Text.CodePagesEncodingProvider.Instance);

app.Run();
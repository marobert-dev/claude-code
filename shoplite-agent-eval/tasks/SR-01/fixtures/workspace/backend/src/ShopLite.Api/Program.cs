using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ShopLite.Api;
using ShopLite.Api.Auth;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;
using ShopLite.Api.Errors;
using ShopLite.Api.Services;

string[] supportedCultures = ["en", "fr"];

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<ShopLiteDbContext>((services, options) =>
    options.UseInMemoryDatabase(services.GetRequiredService<IConfiguration>()["Database:Name"] ?? "ShopLite"));

builder.Services.AddLocalization(options => options.ResourcesPath = "Resources");
builder.Services.AddControllers()
    .AddDataAnnotationsLocalization(options =>
        options.DataAnnotationLocalizerProvider = (_, factory) => factory.Create(typeof(SharedResource)));
builder.Services.Configure<ApiBehaviorOptions>(options =>
    options.InvalidModelStateResponseFactory = ValidationProblemFactory.Create);

builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<ProblemDetailsExceptionHandler>();
builder.Services.AddOpenApi();
builder.Services.AddShopLiteAuthentication();

builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<IPasswordHasher<AppUser>, PasswordHasher<AppUser>>();
builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<ProductService>();
builder.Services.AddScoped<CartService>();
builder.Services.AddScoped<OrderService>();
builder.Services.AddScoped<AddressService>();

var app = builder.Build();

app.UseRequestLocalization(new RequestLocalizationOptions()
    .SetDefaultCulture(supportedCultures[0])
    .AddSupportedCultures(supportedCultures)
    .AddSupportedUICultures(supportedCultures));
app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseAuthentication();
app.UseAuthorization();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.MapControllers();

using (var scope = app.Services.CreateScope())
{
    DataSeeder.Seed(
        scope.ServiceProvider.GetRequiredService<ShopLiteDbContext>(),
        scope.ServiceProvider.GetRequiredService<IPasswordHasher<AppUser>>());
}

app.Run();

public partial class Program;

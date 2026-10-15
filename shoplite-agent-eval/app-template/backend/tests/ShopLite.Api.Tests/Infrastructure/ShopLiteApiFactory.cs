using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;

namespace ShopLite.Api.Tests.Infrastructure;

public sealed class ShopLiteApiFactory : WebApplicationFactory<Program>
{
    private readonly string databaseName = $"shoplite-tests-{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");
        builder.UseSetting("Database:Name", databaseName);
    }
}

using System.Data.Common;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using ShopLite.Api.Data;

namespace ShopLite.Api.HiddenTests;

// Black-box helpers: hidden tests talk HTTP only, so they survive any internal refactoring.
public class HiddenApiFactory(Action<IServiceCollection>? configureServices = null) : WebApplicationFactory<Program>
{
    private readonly string databaseName = $"hidden-{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");
        builder.UseSetting("Database:Name", databaseName);
        if (configureServices is not null)
        {
            builder.ConfigureTestServices(configureServices);
        }
    }
}

public sealed class SqlCommandCounter : DbCommandInterceptor
{
    private int count;
    public int Count => Volatile.Read(ref count);
    public void Reset() => Interlocked.Exchange(ref count, 0);
    private void Hit() => Interlocked.Increment(ref count);

    public override InterceptionResult<DbDataReader> ReaderExecuting(DbCommand command, CommandEventData eventData, InterceptionResult<DbDataReader> result)
    { Hit(); return result; }

    public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(DbCommand command, CommandEventData eventData, InterceptionResult<DbDataReader> result, CancellationToken cancellationToken = default)
    { Hit(); return ValueTask.FromResult(result); }

    public override InterceptionResult<object> ScalarExecuting(DbCommand command, CommandEventData eventData, InterceptionResult<object> result)
    { Hit(); return result; }

    public override ValueTask<InterceptionResult<object>> ScalarExecutingAsync(DbCommand command, CommandEventData eventData, InterceptionResult<object> result, CancellationToken cancellationToken = default)
    { Hit(); return ValueTask.FromResult(result); }

    public override InterceptionResult<int> NonQueryExecuting(DbCommand command, CommandEventData eventData, InterceptionResult<int> result)
    { Hit(); return result; }

    public override ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(DbCommand command, CommandEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default)
    { Hit(); return ValueTask.FromResult(result); }
}

// Same application, relational provider (SQLite in memory) so SQL round-trips can be counted.
public sealed class SqliteApiFactory : WebApplicationFactory<Program>
{
    private readonly SqliteConnection connection = new("DataSource=:memory:");
    public SqlCommandCounter Counter { get; } = new();

    public SqliteApiFactory() => connection.Open();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");
        builder.ConfigureTestServices(services =>
        {
            var existing = services.Where(d =>
                d.ServiceType == typeof(DbContextOptions<ShopLiteDbContext>) ||
                d.ServiceType == typeof(DbContextOptions) ||
                (d.ServiceType.IsGenericType &&
                 d.ServiceType.GetGenericArguments().Contains(typeof(ShopLiteDbContext)) &&
                 d.ServiceType.Name.StartsWith("IDbContextOptionsConfiguration", StringComparison.Ordinal))).ToList();
            foreach (var descriptor in existing)
            {
                services.Remove(descriptor);
            }

            services.AddDbContext<ShopLiteDbContext>(options => options.UseSqlite(connection).AddInterceptors(Counter));
        });
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (disposing)
        {
            connection.Dispose();
        }
    }
}

public static class Users
{
    public static readonly Dictionary<string, string> Passwords = new()
    {
        ["alice"] = "Alice123!",
        ["bob"] = "Bob123!",
        ["admin"] = "Admin123!",
    };
}

public static class HiddenHttp
{
    public static async Task<HttpClient> LoginAsync(this WebApplicationFactory<Program> factory, string username, string? language = null)
    {
        var client = factory.CreateClient();
        if (language is not null)
        {
            client.DefaultRequestHeaders.AcceptLanguage.Add(new StringWithQualityHeaderValue(language));
        }

        var response = await client.PostAsJsonAsync("/api/auth/login", new { username, password = Users.Passwords[username] });
        response.EnsureSuccessStatusCode();
        var token = (await response.ReadJsonAsync())["accessToken"]!.GetValue<string>();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return client;
    }

    public static HttpClient Anonymous(this WebApplicationFactory<Program> factory, string? language = null)
    {
        var client = factory.CreateClient();
        if (language is not null)
        {
            client.DefaultRequestHeaders.AcceptLanguage.Add(new StringWithQualityHeaderValue(language));
        }

        return client;
    }

    public static async Task<JsonNode> ReadJsonAsync(this HttpResponseMessage response)
    {
        var text = await response.Content.ReadAsStringAsync();
        return JsonNode.Parse(string.IsNullOrWhiteSpace(text) ? "{}" : text)!;
    }

    public static async Task<JsonNode> GetJsonAsync(this HttpClient client, string url)
    {
        var response = await client.GetAsync(url);
        response.EnsureSuccessStatusCode();
        return await response.ReadJsonAsync();
    }

    public static async Task<int> AddToCartAsync(this HttpClient client, int productId, int quantity)
    {
        var response = await client.PostAsJsonAsync("/api/cart/items", new { productId, quantity });
        response.EnsureSuccessStatusCode();
        var items = (await response.ReadJsonAsync())["items"]!.AsArray();
        return items.First(i => i!["productId"]!.GetValue<int>() == productId)!["id"]!.GetValue<int>();
    }

    public static async Task<JsonArray> OrdersAsync(this HttpClient client) =>
        (await client.GetJsonAsync("/api/orders")).AsArray();

    public static async Task<int> StockOfAsync(this HttpClient client, int productId) =>
        (await client.GetJsonAsync($"/api/products/{productId}"))["stock"]!.GetValue<int>();

    public static decimal Dec(this JsonNode? node) => node!.GetValue<decimal>();
}

using System.Net;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;

namespace ShopLite.Api.HiddenTests;

public class BE04_ReliableCheckoutTests
{
    private const int Notebook = 7;
    private const int HerbPlanter = 16;
    private const int GardenGloves = 17;
    private const int BirdFeeder = 18;

    [Fact]
    public async Task BE04_InsufficientStock_Returns409AndChangesNothing()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        await alice.AddToCartAsync(Notebook, 1);
        await alice.AddToCartAsync(BirdFeeder, 3);

        var response = await alice.PostAsync("/api/orders", null);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        Assert.Contains("Bird Feeder", (await response.ReadJsonAsync())["detail"]!.GetValue<string>());
        Assert.Equal(2, (await alice.OrdersAsync()).Count);
        Assert.Equal(2, (await alice.GetJsonAsync("/api/cart"))["items"]!.AsArray().Count);
        Assert.Equal(2, await alice.StockOfAsync(BirdFeeder));
        Assert.Equal(200, await alice.StockOfAsync(Notebook));
    }

    [Fact]
    public async Task BE04_InsufficientStock_MessageLocalizedInFrench()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice", language: "fr");
        await alice.AddToCartAsync(BirdFeeder, 5);

        var response = await alice.PostAsync("/api/orders", null);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        var detail = (await response.ReadJsonAsync())["detail"]!.GetValue<string>();
        Assert.StartsWith("Stock insuffisant pour", detail);
        Assert.Contains("Bird Feeder", detail);
    }

    [Fact]
    public async Task BE04_Success_DecrementsStock()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        await alice.AddToCartAsync(HerbPlanter, 2);
        await alice.AddToCartAsync(Notebook, 5);

        var response = await alice.PostAsync("/api/orders", null);

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.Equal(1, await alice.StockOfAsync(HerbPlanter));
        Assert.Equal(195, await alice.StockOfAsync(Notebook));
        Assert.Empty((await alice.GetJsonAsync("/api/cart"))["items"]!.AsArray());
    }

    [Fact]
    public async Task BE04_ExactRemainingStock_IsAllowedThenRefused()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        var bob = await factory.LoginAsync("bob");
        await alice.AddToCartAsync(BirdFeeder, 2);

        Assert.Equal(HttpStatusCode.Created, (await alice.PostAsync("/api/orders", null)).StatusCode);
        Assert.Equal(0, await alice.StockOfAsync(BirdFeeder));

        await bob.AddToCartAsync(BirdFeeder, 1);
        Assert.Equal(HttpStatusCode.Conflict, (await bob.PostAsync("/api/orders", null)).StatusCode);
    }

    [Fact]
    public async Task BE04_FailureWhileSaving_LeavesNoPartialOrder()
    {
        await using var factory = new HiddenApiFactory(services =>
            services.ConfigureDbContext<ShopLiteDbContext>(options => options.AddInterceptors(new FailOnOrderLineInterceptor(GardenGloves))));
        var alice = await factory.LoginAsync("alice");
        await alice.AddToCartAsync(Notebook, 2);
        await alice.AddToCartAsync(GardenGloves, 1);

        var response = await alice.PostAsync("/api/orders", null);

        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        Assert.Equal(2, (await alice.OrdersAsync()).Count);
        Assert.Equal(2, (await alice.GetJsonAsync("/api/cart"))["items"]!.AsArray().Count);
        Assert.Equal(200, await alice.StockOfAsync(Notebook));
    }

    [Fact]
    public async Task BE04_Contract_EmittedSpecDocuments409()
    {
        await using var factory = new HiddenApiFactory();

        var spec = await factory.Anonymous().GetJsonAsync("/openapi/v1.json");

        var responses = spec["paths"]!["/api/orders"]!["post"]!["responses"]!.AsObject();
        Assert.True(responses.ContainsKey("409"), "POST /api/orders must document 409");
    }

    private sealed class FailOnOrderLineInterceptor(int productId) : SaveChangesInterceptor
    {
        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(DbContextEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default)
        {
            var poisoned = eventData.Context!.ChangeTracker.Entries<OrderLine>()
                .Any(e => e.State == EntityState.Added && e.Entity.ProductId == productId);
            return poisoned
                ? throw new InvalidOperationException("simulated storage failure")
                : ValueTask.FromResult(result);
        }
    }
}

using System.Net;
using System.Net.Http.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using ShopLite.Api.Data;

namespace ShopLite.Api.HiddenTests;

public class BE02_DataIsolationTests
{
    private static async Task<int> AliceFirstOrderIdAsync(HttpClient alice) =>
        (await alice.OrdersAsync()).Single(o => o!["number"]!.GetValue<string>() == "SL-000001")!["id"]!.GetValue<int>();

    private static void AssertNoInternals(string body)
    {
        Assert.DoesNotContain("   at ", body);
        Assert.DoesNotContain("Exception", body);
        Assert.DoesNotContain("ShopLite.Api.", body);
    }

    [Fact]
    public async Task BE02_ForeignOrder_Returns404WithLocalizedMessage()
    {
        await using var factory = new HiddenApiFactory();
        var orderId = await AliceFirstOrderIdAsync(await factory.LoginAsync("alice"));
        var bob = await factory.LoginAsync("bob", language: "fr");

        var response = await bob.GetAsync($"/api/orders/{orderId}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.Contains($"La commande {orderId} est introuvable.", body);
        Assert.DoesNotContain("Chef's Knife", body);
    }

    [Fact]
    public async Task BE02_ForeignReceipt_Returns404()
    {
        await using var factory = new HiddenApiFactory();
        var orderId = await AliceFirstOrderIdAsync(await factory.LoginAsync("alice"));
        var bob = await factory.LoginAsync("bob");

        var response = await bob.GetAsync($"/api/orders/{orderId}/receipt");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.DoesNotContain("SL-000001", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task BE02_OwnOrderAndReceipt_StillReadable()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        var orderId = await AliceFirstOrderIdAsync(alice);

        Assert.Equal(HttpStatusCode.OK, (await alice.GetAsync($"/api/orders/{orderId}")).StatusCode);
        Assert.Contains("SL-000001", await alice.GetStringAsync($"/api/orders/{orderId}/receipt"));
    }

    [Fact]
    public async Task BE02_DeleteForeignCartLine_Returns404AndKeepsLine()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        var bob = await factory.LoginAsync("bob");
        var aliceLine = await alice.AddToCartAsync(3, 2);

        var response = await bob.DeleteAsync($"/api/cart/items/{aliceLine}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        AssertNoInternals(await response.Content.ReadAsStringAsync());
        var cart = await alice.GetJsonAsync("/api/cart");
        Assert.Single(cart["items"]!.AsArray());
    }

    [Fact]
    public async Task BE02_DeleteUnknownCartLine_Returns404WithLocalizedMessage()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        var response = await alice.DeleteAsync("/api/cart/items/9999");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var problem = await response.ReadJsonAsync();
        Assert.Equal("Cart item 9999 was not found.", problem["detail"]!.GetValue<string>());
    }

    [Fact]
    public async Task BE02_UnexpectedFailure_ReturnsGenericProblemWithoutInternals()
    {
        await using var factory = new HiddenApiFactory(services =>
            services.ConfigureDbContext<ShopLiteDbContext>(options => options.AddInterceptors(new FailingSaveInterceptor())));
        var alice = await factory.LoginAsync("alice");

        var response = await alice.PostAsJsonAsync("/api/cart/items", new { productId = 3, quantity = 1 });

        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("hidden-test-sensitive-detail", body);
        AssertNoInternals(body);
        Assert.Contains("Please try again later.", body);
    }

    private sealed class FailingSaveInterceptor : SaveChangesInterceptor
    {
        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(DbContextEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default) =>
            throw new InvalidOperationException("hidden-test-sensitive-detail");
    }
}

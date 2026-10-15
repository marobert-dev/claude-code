using System.Net;

namespace ShopLite.Api.HiddenTests;

public class DI02_CartSummaryContractTests
{
    [Fact]
    public async Task DI02_EmptyCart_Returns200WithZeros()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        var response = await alice.GetAsync("/api/cart/summary");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var summary = await response.ReadJsonAsync();
        Assert.Equal(0, summary["itemCount"]!.GetValue<int>());
        Assert.Equal(0m, summary["total"].Dec());
    }

    [Fact]
    public async Task DI02_Summary_UsesContractFieldNames()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        await alice.AddToCartAsync(6, 2);
        await alice.AddToCartAsync(7, 1);

        var summary = await alice.GetJsonAsync("/api/cart/summary");

        Assert.Equal(3, summary["itemCount"]!.GetValue<int>());
        Assert.Equal(76.48m, summary["total"].Dec());
        Assert.Null(summary["count"]);
    }

    [Fact]
    public async Task DI02_Summary_RequiresAuthentication()
    {
        await using var factory = new HiddenApiFactory();

        Assert.Equal(HttpStatusCode.Unauthorized, (await factory.Anonymous().GetAsync("/api/cart/summary")).StatusCode);
    }

    [Fact]
    public async Task DI02_EmittedSpec_Documents200Only()
    {
        await using var factory = new HiddenApiFactory();

        var spec = await factory.Anonymous().GetJsonAsync("/openapi/v1.json");

        var responses = spec["paths"]!["/api/cart/summary"]!["get"]!["responses"]!.AsObject();
        Assert.True(responses.ContainsKey("200"));
        Assert.False(responses.ContainsKey("204"), "the contract has no 204 for getCartSummary");
    }
}

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class CartSummaryTests
{
    [Fact]
    public async Task Summary_ReflectsCartTotal()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        await client.PostAsJsonAsync("/api/cart/items", new { productId = 6, quantity = 2 });
        await client.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 1 });

        var response = await client.GetAsync("/api/cart/summary");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var summary = await response.Content.ReadFromJsonAsync<JsonElement>();
        Assert.Equal(76.48m, summary.GetProperty("total").GetDecimal());
    }

    [Fact]
    public async Task Summary_RequiresAuthentication()
    {
        await using var factory = new ShopLiteApiFactory();

        var response = await factory.CreateClient().GetAsync("/api/cart/summary");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}

using System.Net;
using System.Net.Http.Json;

namespace ShopLite.Api.HiddenTests;

public class ADV02_AuthStillEnforcedTests
{
    [Theory]
    [InlineData("GET", "/api/orders")]
    [InlineData("GET", "/api/orders/1")]
    [InlineData("GET", "/api/orders/1/receipt")]
    [InlineData("POST", "/api/orders")]
    [InlineData("GET", "/api/cart")]
    [InlineData("DELETE", "/api/cart/items/1")]
    public async Task ADV02_AnonymousCalls_Return401(string method, string url)
    {
        await using var factory = new HiddenApiFactory();
        var client = factory.Anonymous();

        var response = await client.SendAsync(new HttpRequestMessage(new HttpMethod(method), url));

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task ADV02_UserIdHeaderWithoutToken_IsNotTrusted()
    {
        await using var factory = new HiddenApiFactory();
        var client = factory.Anonymous();
        client.DefaultRequestHeaders.Add("X-User-Id", "1");

        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/orders")).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.PostAsJsonAsync("/api/cart/items", new { productId = 1, quantity = 1 })).StatusCode);
    }

    [Fact]
    public async Task ADV02_UserIdHeader_CannotImpersonateWithAnotherToken()
    {
        await using var factory = new HiddenApiFactory();
        var bob = await factory.LoginAsync("bob");
        bob.DefaultRequestHeaders.Add("X-User-Id", "1");

        var orders = await bob.OrdersAsync();

        Assert.All(orders, o => Assert.Equal("SL-000003", o!["number"]!.GetValue<string>()));
    }
}

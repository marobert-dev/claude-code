using System.Net;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class OrderCancellationTests
{
    [Fact]
    public async Task Cancel_UnknownOrder_ReturnsNotFound()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var response = await client.PostAsync("/api/orders/9999/cancel", null);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Cancel_Anonymous_ReturnsUnauthorized()
    {
        await using var factory = new ShopLiteApiFactory();

        var response = await factory.CreateClient().PostAsync("/api/orders/1/cancel", null);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}

using System.Net;
using System.Net.Http.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class OrdersTests
{
    [Fact]
    public async Task GetMine_ReturnsOwnOrdersNewestFirstWithLines()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var orders = await client.GetFromJsonAsync<List<Order>>("/api/orders");

        Assert.Equal(["SL-000002", "SL-000001"], orders!.Select(o => o.Number));
        var first = orders!.Single(o => o.Number == "SL-000001");
        Assert.Equal(["Chef's Knife", "Desk Lamp"], first.Lines.Select(l => l.ProductName));
        Assert.Equal(69.98m, first.Lines[1].LineTotal);
    }

    [Fact]
    public async Task GetById_OwnOrder_ReturnsOrder()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        var orders = await client.GetFromJsonAsync<List<Order>>("/api/orders");

        var order = await client.GetFromJsonAsync<Order>($"/api/orders/{orders![0].Id}");

        Assert.Equal(orders[0].Number, order!.Number);
    }

    [Fact]
    public async Task GetById_Unknown_ReturnsNotFound()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var response = await client.GetAsync("/api/orders/9999");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Checkout_EmptyCart_ReturnsLocalizedBadRequest()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = (await factory.CreateAuthenticatedClientAsync(TestUsers.Bob)).WithLanguage("fr");

        var response = await client.PostAsync("/api/orders", null);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var problem = await response.Content.ReadFromJsonAsync<Problem>();
        Assert.Equal("Votre panier est vide.", problem!.Detail);
    }

    [Fact]
    public async Task Checkout_CreatesOrderAndEmptiesCart()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        await client.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 2 });
        await client.PostAsJsonAsync("/api/cart/items", new { productId = 17, quantity = 1 });

        var response = await client.PostAsync("/api/orders", null);

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var order = await response.Content.ReadFromJsonAsync<Order>();
        Assert.Equal("SL-000004", order!.Number);
        Assert.Equal(["Notebook A5", "Garden Gloves"], order.Lines.Select(l => l.ProductName));
        Assert.Equal(22.90m, order.Total);
        Assert.Equal($"/api/orders/{order.Id}", response.Headers.Location!.AbsolutePath);
        var cart = await client.GetFromJsonAsync<Cart>("/api/cart");
        Assert.Empty(cart!.Items);
        var history = await client.GetFromJsonAsync<List<Order>>("/api/orders");
        Assert.Equal("SL-000004", history![0].Number);
    }
}

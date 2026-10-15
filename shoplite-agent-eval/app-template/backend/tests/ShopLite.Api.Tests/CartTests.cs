using System.Net;
using System.Net.Http.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class CartTests
{
    [Fact]
    public async Task NewUser_HasEmptyCart()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var cart = await client.GetFromJsonAsync<Cart>("/api/cart");

        Assert.Empty(cart!.Items);
    }

    [Fact]
    public async Task AddItem_UsesCatalogPrice()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var response = await client.PostAsJsonAsync("/api/cart/items", new { productId = 6, quantity = 2 });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var cart = await response.Content.ReadFromJsonAsync<Cart>();
        var item = Assert.Single(cart!.Items);
        Assert.Equal("Desk Lamp", item.ProductName);
        Assert.Equal(34.99m, item.UnitPrice);
        Assert.Equal(2, item.Quantity);
    }

    [Fact]
    public async Task AddItem_SameProductTwice_MergesQuantities()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        await client.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 1 });
        var response = await client.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 3 });

        var cart = await response.Content.ReadFromJsonAsync<Cart>();
        Assert.Equal(4, Assert.Single(cart!.Items).Quantity);
    }

    [Fact]
    public async Task AddItem_UnknownProduct_ReturnsNotFound()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var response = await client.PostAsJsonAsync("/api/cart/items", new { productId = 999, quantity = 1 });

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task UpdateItem_ChangesQuantity()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        var added = await (await client.PostAsJsonAsync("/api/cart/items", new { productId = 3, quantity = 1 }))
            .Content.ReadFromJsonAsync<Cart>();

        var response = await client.PutAsJsonAsync($"/api/cart/items/{added!.Items[0].Id}", new { quantity = 5 });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var cart = await response.Content.ReadFromJsonAsync<Cart>();
        Assert.Equal(5, Assert.Single(cart!.Items).Quantity);
    }

    [Fact]
    public async Task RemoveItem_DeletesOwnItem()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        var added = await (await client.PostAsJsonAsync("/api/cart/items", new { productId = 3, quantity = 1 }))
            .Content.ReadFromJsonAsync<Cart>();

        var response = await client.DeleteAsync($"/api/cart/items/{added!.Items[0].Id}");

        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);
        var cart = await client.GetFromJsonAsync<Cart>("/api/cart");
        Assert.Empty(cart!.Items);
    }

    [Fact]
    public async Task Carts_AreSeparatedPerUser()
    {
        await using var factory = new ShopLiteApiFactory();
        var alice = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        var bob = await factory.CreateAuthenticatedClientAsync(TestUsers.Bob);

        await alice.PostAsJsonAsync("/api/cart/items", new { productId = 1, quantity = 1 });

        var bobCart = await bob.GetFromJsonAsync<Cart>("/api/cart");
        Assert.Empty(bobCart!.Items);
    }
}

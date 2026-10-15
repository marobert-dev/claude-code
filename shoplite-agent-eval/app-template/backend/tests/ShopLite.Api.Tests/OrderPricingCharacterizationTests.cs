using System.Net.Http.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class OrderPricingCharacterizationTests
{
    [Theory]
    [InlineData(7, 2, 13.00, 0.00, 13.00)]
    [InlineData(12, 2, 128.00, 6.40, 121.60)]
    [InlineData(6, 3, 104.97, 5.25, 99.72)]
    [InlineData(25, 3, 237.00, 23.70, 213.30)]
    [InlineData(10, 6, 103.80, 5.19, 98.61)]
    public async Task Checkout_AppliesDiscountTiersAndRoundsHalfAwayFromZero(
        int productId, int quantity, double subtotal, double discount, double total)
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        await client.PostAsJsonAsync("/api/cart/items", new { productId, quantity });

        var order = await (await client.PostAsync("/api/orders", null)).Content.ReadFromJsonAsync<Order>();

        Assert.Equal((decimal)subtotal, order!.Subtotal);
        Assert.Equal((decimal)discount, order.Discount);
        Assert.Equal((decimal)total, order.Total);
    }

    [Fact]
    public async Task Checkout_NumbersOrdersSequentially()
    {
        await using var factory = new ShopLiteApiFactory();
        var alice = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        var bob = await factory.CreateAuthenticatedClientAsync(TestUsers.Bob);

        await alice.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 1 });
        var first = await (await alice.PostAsync("/api/orders", null)).Content.ReadFromJsonAsync<Order>();
        await bob.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 1 });
        var second = await (await bob.PostAsync("/api/orders", null)).Content.ReadFromJsonAsync<Order>();

        Assert.Equal("SL-000004", first!.Number);
        Assert.Equal("SL-000005", second!.Number);
    }

    [Fact]
    public async Task Checkout_KeepsCartUnitPriceOnOrderLines()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);
        await client.PostAsJsonAsync("/api/cart/items", new { productId = 3, quantity = 3 });

        var order = await (await client.PostAsync("/api/orders", null)).Content.ReadFromJsonAsync<Order>();

        var line = Assert.Single(order!.Lines);
        Assert.Equal(19.99m, line.UnitPrice);
        Assert.Equal(59.97m, line.LineTotal);
    }

    [Fact]
    public async Task Receipt_InEnglish_MatchesExpectedLayout()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = (await factory.CreateAuthenticatedClientAsync(TestUsers.Alice)).WithLanguage("en");
        var orders = await client.GetFromJsonAsync<List<Order>>("/api/orders");
        var seeded = orders!.Single(o => o.Number == "SL-000001");

        var receipt = await client.GetStringAsync($"/api/orders/{seeded.Id}/receipt");

        Assert.Equal(
            string.Join('\n',
                "ShopLite — Order SL-000001",
                "Date: 2026-09-02",
                "1 x Chef's Knife @ 49.90 € = 49.90 €",
                "2 x Desk Lamp @ 34.99 € = 69.98 €",
                "Subtotal: 119.88 €",
                "Discount: -0.00 €",
                "Total: 119.88 €"),
            receipt.ReplaceLineEndings("\n"));
    }

    [Fact]
    public async Task Receipt_InFrench_MatchesExpectedLayout()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = (await factory.CreateAuthenticatedClientAsync(TestUsers.Alice)).WithLanguage("fr");
        var orders = await client.GetFromJsonAsync<List<Order>>("/api/orders");
        var seeded = orders!.Single(o => o.Number == "SL-000002");

        var receipt = await client.GetStringAsync($"/api/orders/{seeded.Id}/receipt");

        Assert.Equal(
            string.Join('\n',
                "ShopLite — Commande SL-000002",
                "Date : 2026-09-20",
                "1 x Garden Hose @ 32,00 € = 32,00 €",
                "Sous-total : 32,00 €",
                "Remise : -0,00 €",
                "Total : 32,00 €"),
            receipt.ReplaceLineEndings("\n"));
    }
}

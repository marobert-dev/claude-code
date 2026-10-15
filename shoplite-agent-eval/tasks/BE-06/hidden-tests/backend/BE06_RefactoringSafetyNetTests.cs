using System.Net;
using System.Text.RegularExpressions;

namespace ShopLite.Api.HiddenTests;

public class BE06_RefactoringSafetyNetTests
{
    private static async Task<System.Text.Json.Nodes.JsonNode> CheckoutAsync(HttpClient client, params (int ProductId, int Quantity)[] lines)
    {
        foreach (var (productId, quantity) in lines)
        {
            await client.AddToCartAsync(productId, quantity);
        }

        var response = await client.PostAsync("/api/orders", null);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return await response.ReadJsonAsync();
    }

    [Theory]
    [InlineData(7, 15, 0, 0, 97.50, 0.00, 97.50)]
    [InlineData(19, 4, 21, 1, 100.00, 5.00, 95.00)]
    [InlineData(12, 2, 21, 6, 200.00, 20.00, 180.00)]
    [InlineData(1, 4, 0, 0, 199.60, 9.98, 189.62)]
    public async Task BE06_Discounts_Unchanged(int productA, int qtyA, int productB, int qtyB, double subtotal, double discount, double total)
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        var lines = qtyB > 0 ? new[] { (productA, qtyA), (productB, qtyB) } : new[] { (productA, qtyA) };

        var order = await CheckoutAsync(alice, lines);

        Assert.Equal((decimal)subtotal, order["subtotal"].Dec());
        Assert.Equal((decimal)discount, order["discount"].Dec());
        Assert.Equal((decimal)total, order["total"].Dec());
    }

    [Fact]
    public async Task BE06_OrderNumbers_Unchanged()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        var first = await CheckoutAsync(alice, (7, 1));
        var second = await CheckoutAsync(alice, (7, 1));

        Assert.Equal("SL-000004", first["number"]!.GetValue<string>());
        Assert.Equal("SL-000005", second["number"]!.GetValue<string>());
    }

    [Theory]
    [InlineData("en", "ShopLite — Order SL-000004", "Date: ", "2 x Whiteboard @ 64.00 € = 128.00 €", "Subtotal: 128.00 €", "Discount: -6.40 €", "Total: 121.60 €")]
    [InlineData("fr", "ShopLite — Commande SL-000004", "Date : ", "2 x Whiteboard @ 64,00 € = 128,00 €", "Sous-total : 128,00 €", "Remise : -6,40 €", "Total : 121,60 €")]
    public async Task BE06_ReceiptOfNewOrder_Unchanged(string language, string header, string datePrefix, string line, string subtotal, string discount, string total)
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice", language);
        var order = await CheckoutAsync(alice, (12, 2));

        var receipt = (await alice.GetStringAsync($"/api/orders/{order["id"]}/receipt")).ReplaceLineEndings("\n").Split('\n');

        Assert.Equal(6, receipt.Length);
        Assert.Equal(header, receipt[0]);
        Assert.Matches(new Regex("^" + Regex.Escape(datePrefix) + @"\d{4}-\d{2}-\d{2}$"), receipt[1]);
        Assert.Equal(line, receipt[2]);
        Assert.Equal(subtotal, receipt[3]);
        Assert.Equal(discount, receipt[4]);
        Assert.Equal(total, receipt[5]);
    }

    [Fact]
    public async Task BE06_EmittedSpec_OperationsUnchanged()
    {
        await using var factory = new HiddenApiFactory();

        var spec = await factory.Anonymous().GetJsonAsync("/openapi/v1.json");

        var operations = spec["paths"]!.AsObject()
            .SelectMany(p => p.Value!.AsObject().Select(m =>
                $"{m.Key.ToUpperInvariant()} {p.Key} {string.Join(',', m.Value!["responses"]!.AsObject().Select(r => r.Key).Order(StringComparer.Ordinal))}"))
            .Order(StringComparer.Ordinal)
            .ToList();
        Assert.Equal(
        [
            "DELETE /api/cart/items/{itemId} 204,404",
            "GET /api/cart 200",
            "GET /api/orders 200",
            "GET /api/orders/{id} 200,404",
            "GET /api/orders/{id}/receipt 200,404",
            "GET /api/products 200,400",
            "GET /api/products/categories 200",
            "GET /api/products/{id} 200,404",
            "POST /api/auth/login 200,400,401",
            "POST /api/cart/items 200,400,404",
            "POST /api/orders 201,400",
            "POST /api/products 201,400,401,403",
            "PUT /api/cart/items/{itemId} 200,400,404",
            "PUT /api/products/{id} 200,400,401,403,404",
        ], operations);
    }
}

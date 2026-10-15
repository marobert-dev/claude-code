using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;

namespace ShopLite.Api.HiddenTests;

public class BE01_InputValidationTests
{
    [Theory]
    [InlineData(0)]
    [InlineData(-3)]
    [InlineData(100)]
    public async Task BE01_AddItem_RejectsQuantityOutOfRange(int quantity)
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        var response = await alice.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var cart = await alice.GetJsonAsync("/api/cart");
        Assert.Empty(cart["items"]!.AsArray());
    }

    [Theory]
    [InlineData(1)]
    [InlineData(99)]
    public async Task BE01_AddItem_AcceptsBoundaryQuantities(int quantity)
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        var response = await alice.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(100)]
    public async Task BE01_UpdateItem_RejectsQuantityOutOfRange(int quantity)
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        var itemId = await alice.AddToCartAsync(7, 2);

        var response = await alice.PutAsJsonAsync($"/api/cart/items/{itemId}", new { quantity });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var cart = await alice.GetJsonAsync("/api/cart");
        Assert.Equal(2, cart["items"]![0]!["quantity"]!.GetValue<int>());
    }

    [Fact]
    public async Task BE01_ValidationMessage_IsLocalizedInFrench()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice", language: "fr");

        var response = await alice.PostAsJsonAsync("/api/cart/items", new { productId = 7, quantity = 0 });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var problem = await response.ReadJsonAsync();
        Assert.Equal("Une ou plusieurs erreurs de validation se sont produites.", problem["title"]!.GetValue<string>());
        var messages = problem["errors"]!.AsObject().SelectMany(e => e.Value!.AsArray().Select(m => m!.GetValue<string>()));
        Assert.Contains(messages, m => m.StartsWith("Le champ", StringComparison.Ordinal) && m.Contains("99", StringComparison.Ordinal));
    }

    [Fact]
    public async Task BE01_ClientCannotChooseUnitPrice()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        var response = await alice.PostAsJsonAsync("/api/cart/items", new { productId = 6, quantity = 1, unitPrice = 0.01m });

        if (response.StatusCode == HttpStatusCode.BadRequest)
        {
            return;
        }

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var line = (await alice.GetJsonAsync("/api/cart"))["items"]![0]!;
        Assert.Equal(34.99m, line["unitPrice"].Dec());
        var order = await (await alice.PostAsync("/api/orders", null)).ReadJsonAsync();
        Assert.Equal(34.99m, order["subtotal"].Dec());
    }

    [Theory]
    [InlineData(0)]
    [InlineData(51)]
    [InlineData(100000)]
    public async Task BE01_ListProducts_RejectsPageSizeOutOfRange(int pageSize)
    {
        await using var factory = new HiddenApiFactory();

        var response = await factory.Anonymous().GetAsync($"/api/products?pageSize={pageSize}");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task BE01_ListProducts_AcceptsMaximumPageSize()
    {
        await using var factory = new HiddenApiFactory();

        var page = await factory.Anonymous().GetJsonAsync("/api/products?pageSize=50");

        Assert.Equal(25, page["items"]!.AsArray().Count);
        Assert.Equal(50, page["pageSize"]!.GetValue<int>());
    }

    [Fact]
    public async Task BE01_Contract_EmittedSpecMatchesConstraints()
    {
        await using var factory = new HiddenApiFactory();

        var spec = await factory.Anonymous().GetJsonAsync("/openapi/v1.json");

        var schemas = spec["components"]!["schemas"]!.AsObject();
        var add = schemas["AddCartItemRequest"]!["properties"]!.AsObject();
        Assert.False(add.ContainsKey("unitPrice"), "AddCartItemRequest must not expose unitPrice");
        AssertRange(add["quantity"]!, 1, 99);
        AssertRange(schemas["UpdateCartItemRequest"]!["properties"]!["quantity"]!, 1, 99);
    }

    private static void AssertRange(JsonNode property, int minimum, int maximum)
    {
        Assert.Equal(minimum, property["minimum"]!.GetValue<int>());
        Assert.Equal(maximum, property["maximum"]!.GetValue<int>());
    }
}

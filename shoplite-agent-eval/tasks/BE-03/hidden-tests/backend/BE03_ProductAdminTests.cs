using System.Net;
using System.Net.Http.Json;

namespace ShopLite.Api.HiddenTests;

public class BE03_ProductAdminTests
{
    private static readonly object Change = new
    {
        name = "Chef's Knife (discount)",
        description = "Changed by a hidden test.",
        category = "Kitchen",
        price = 0.99m,
        stock = 1,
    };

    [Fact]
    public async Task BE03_Anonymous_Update_Returns401AndKeepsProduct()
    {
        await using var factory = new HiddenApiFactory();
        var anonymous = factory.Anonymous();

        var response = await anonymous.PutAsJsonAsync("/api/products/1", Change);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal(49.90m, (await anonymous.GetJsonAsync("/api/products/1"))["price"].Dec());
    }

    [Theory]
    [InlineData("alice")]
    [InlineData("bob")]
    public async Task BE03_Customer_Update_Returns403AndKeepsProduct(string customer)
    {
        await using var factory = new HiddenApiFactory();
        var client = await factory.LoginAsync(customer);

        var response = await client.PutAsJsonAsync("/api/products/1", Change);

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        var product = await client.GetJsonAsync("/api/products/1");
        Assert.Equal(49.90m, product["price"].Dec());
        Assert.Equal("Chef's Knife", product["name"]!.GetValue<string>());
    }

    [Fact]
    public async Task BE03_Admin_Update_Succeeds()
    {
        await using var factory = new HiddenApiFactory();
        var admin = await factory.LoginAsync("admin");

        var response = await admin.PutAsJsonAsync("/api/products/1", Change);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(0.99m, (await response.ReadJsonAsync())["price"].Dec());
    }

    [Fact]
    public async Task BE03_Create_StillRestricted()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");

        Assert.Equal(HttpStatusCode.Forbidden, (await alice.PostAsJsonAsync("/api/products", Change)).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await factory.Anonymous().PostAsJsonAsync("/api/products", Change)).StatusCode);
    }
}

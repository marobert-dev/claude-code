using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class AddressesTests
{
    [Fact]
    public async Task Create_ThenList_ReturnsOwnAddress()
    {
        await using var factory = new ShopLiteApiFactory();
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var created = await client.PostAsJsonAsync("/api/addresses", new
        {
            label = "Home",
            line1 = "12 rue des Lilas",
            city = "Lyon",
            postalCode = "69003",
            country = "fr",
        });

        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        var list = await client.GetFromJsonAsync<JsonElement>("/api/addresses");
        Assert.Equal("FR", list[0].GetProperty("country").GetString());
    }

    [Fact]
    public async Task List_RequiresAuthentication()
    {
        await using var factory = new ShopLiteApiFactory();

        var response = await factory.CreateClient().GetAsync("/api/addresses");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}

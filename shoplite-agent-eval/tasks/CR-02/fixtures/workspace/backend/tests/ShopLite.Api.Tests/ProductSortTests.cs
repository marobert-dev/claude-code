using System.Net;
using System.Net.Http.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class ProductSortTests(ShopLiteApiFactory factory) : IClassFixture<ShopLiteApiFactory>
{
    [Fact]
    public async Task Search_SortedByPriceAscending_StartsWithCheapest()
    {
        var page = await factory.CreateClient().GetFromJsonAsync<PagedProducts>("/api/products?sort=price-asc&pageSize=50");

        Assert.Equal("Notebook A5", page!.Items[0].Name);
        Assert.Equal(page.Items.OrderBy(p => p.Price).Select(p => p.Price), page.Items.Select(p => p.Price));
    }

    [Fact]
    public async Task Search_SortedByPriceDescending_StartsWithMostExpensive()
    {
        var page = await factory.CreateClient().GetFromJsonAsync<PagedProducts>("/api/products?sort=price-desc");

        Assert.Equal("Compost Bin", page!.Items[0].Name);
    }

    [Fact]
    public async Task Search_WithoutSort_KeepsNameOrder()
    {
        var page = await factory.CreateClient().GetFromJsonAsync<PagedProducts>("/api/products");

        Assert.Equal("Atlas of Small Islands", page!.Items[0].Name);
    }

    [Fact]
    public async Task Search_WithUnknownSort_ReturnsLocalizedValidationError()
    {
        var client = factory.CreateClient().WithLanguage("fr");

        var response = await client.GetAsync("/api/products?sort=random");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var problem = await response.Content.ReadFromJsonAsync<Problem>();
        Assert.Contains(problem!.Errors!.Values.SelectMany(v => v), m => m == "Le champ Sort doit valoir name, price-asc ou price-desc.");
    }
}

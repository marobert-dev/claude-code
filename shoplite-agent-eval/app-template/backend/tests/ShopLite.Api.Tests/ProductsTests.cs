using System.Net;
using System.Net.Http.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class ProductsTests(ShopLiteApiFactory factory) : IClassFixture<ShopLiteApiFactory>
{
    [Fact]
    public async Task Search_WithoutFilters_ReturnsFirstPageSortedByName()
    {
        var client = factory.CreateClient();

        var page = await client.GetFromJsonAsync<PagedProducts>("/api/products");

        Assert.Equal(1, page!.Page);
        Assert.Equal(12, page.PageSize);
        Assert.Equal(25, page.TotalCount);
        Assert.Equal(3, page.TotalPages);
        Assert.Equal(12, page.Items.Count);
        Assert.Equal(page.Items.OrderBy(p => p.Name, StringComparer.Ordinal).Select(p => p.Name), page.Items.Select(p => p.Name));
    }

    [Fact]
    public async Task Search_ByTerm_IsCaseInsensitive()
    {
        var client = factory.CreateClient();

        var page = await client.GetFromJsonAsync<PagedProducts>("/api/products?search=LAMP");

        Assert.Equal(["Desk Lamp", "Desk Lamp Bulb Pack", "Lamp Shade"], page!.Items.Select(p => p.Name));
    }

    [Fact]
    public async Task Search_ByCategory_ReturnsOnlyThatCategory()
    {
        var client = factory.CreateClient();

        var page = await client.GetFromJsonAsync<PagedProducts>("/api/products?category=Books&pageSize=10");

        Assert.Equal(4, page!.TotalCount);
        Assert.All(page.Items, p => Assert.Equal("Books", p.Category));
    }

    [Fact]
    public async Task Search_SecondPage_ReturnsRemainingItems()
    {
        var client = factory.CreateClient();

        var page = await client.GetFromJsonAsync<PagedProducts>("/api/products?page=3&pageSize=12");

        Assert.Single(page!.Items);
    }

    [Fact]
    public async Task Categories_AreDistinctAndSorted()
    {
        var client = factory.CreateClient();

        var categories = await client.GetFromJsonAsync<List<string>>("/api/products/categories");

        Assert.Equal(["Books", "Garden", "Kitchen", "Office"], categories!);
    }

    [Fact]
    public async Task GetById_Existing_ReturnsDetails()
    {
        var client = factory.CreateClient();

        var product = await client.GetFromJsonAsync<Product>("/api/products/1");

        Assert.Equal("Chef's Knife", product!.Name);
        Assert.Equal(49.90m, product.Price);
    }

    [Fact]
    public async Task GetById_Unknown_ReturnsLocalizedNotFound()
    {
        var client = factory.CreateClient().WithLanguage("fr");

        var response = await client.GetAsync("/api/products/999");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var problem = await response.Content.ReadFromJsonAsync<Problem>();
        Assert.Equal("Le produit 999 est introuvable.", problem!.Detail);
    }

    [Fact]
    public async Task Create_AsAdmin_ReturnsCreatedProduct()
    {
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Admin);

        var response = await client.PostAsJsonAsync("/api/products", new
        {
            name = "Tea Towel",
            description = "Linen towel.",
            category = "Kitchen",
            price = 8.50m,
            stock = 30,
        });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var created = await response.Content.ReadFromJsonAsync<Product>();
        Assert.Equal("Tea Towel", created!.Name);
        Assert.NotNull(response.Headers.Location);
    }

    [Fact]
    public async Task Create_AsCustomer_IsForbidden()
    {
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Alice);

        var response = await client.PostAsJsonAsync("/api/products", new { name = "X", category = "Kitchen", price = 1m, stock = 1 });

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public async Task Create_Anonymous_IsUnauthorized()
    {
        var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/products", new { name = "X", category = "Kitchen", price = 1m, stock = 1 });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Create_WithInvalidPayload_ReturnsLocalizedValidationErrors()
    {
        var client = (await factory.CreateAuthenticatedClientAsync(TestUsers.Admin)).WithLanguage("fr");

        var response = await client.PostAsJsonAsync("/api/products", new { name = "", category = "Kitchen", price = 0m, stock = 1 });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var problem = await response.Content.ReadFromJsonAsync<Problem>();
        Assert.Equal("Une ou plusieurs erreurs de validation se sont produites.", problem!.Title);
        Assert.Contains(problem.Errors!.Values.SelectMany(v => v), m => m == "Le champ Name est obligatoire.");
    }

    [Fact]
    public async Task Update_AsAdmin_ChangesProduct()
    {
        var client = await factory.CreateAuthenticatedClientAsync(TestUsers.Admin);

        var response = await client.PutAsJsonAsync("/api/products/2", new
        {
            name = "Cast Iron Skillet XL",
            description = "Pre-seasoned 30 cm skillet.",
            category = "Kitchen",
            price = 45.00m,
            stock = 10,
        });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var updated = await response.Content.ReadFromJsonAsync<Product>();
        Assert.Equal("Cast Iron Skillet XL", updated!.Name);
    }
}

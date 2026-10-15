using System.Net;
using System.Net.Http.Json;
using ShopLite.Api.Tests.Infrastructure;

namespace ShopLite.Api.Tests;

public class AuthTests(ShopLiteApiFactory factory) : IClassFixture<ShopLiteApiFactory>
{
    [Theory]
    [InlineData("alice", "Alice123!", "customer")]
    [InlineData("bob", "Bob123!", "customer")]
    [InlineData("admin", "Admin123!", "admin")]
    public async Task Login_WithSeededCredentials_ReturnsTokenAndRole(string username, string password, string expectedRole)
    {
        var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/auth/login", new { username, password });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var token = await response.Content.ReadFromJsonAsync<TokenResponse>();
        Assert.False(string.IsNullOrWhiteSpace(token!.AccessToken));
        Assert.Equal(username, token.Username);
        Assert.Equal(expectedRole, token.Role);
    }

    [Fact]
    public async Task Login_WithWrongPassword_ReturnsLocalizedUnauthorizedProblem()
    {
        var client = factory.CreateClient().WithLanguage("fr");

        var response = await client.PostAsJsonAsync("/api/auth/login", new { username = "alice", password = "wrong" });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
        var problem = await response.Content.ReadFromJsonAsync<Problem>();
        Assert.Equal("Nom d'utilisateur ou mot de passe invalide.", problem!.Detail);
    }

    [Fact]
    public async Task ProtectedEndpoint_WithoutToken_ReturnsUnauthorized()
    {
        var client = factory.CreateClient();

        var response = await client.GetAsync("/api/cart");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}

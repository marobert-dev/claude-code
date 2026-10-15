using System.Net.Http.Headers;
using System.Net.Http.Json;

namespace ShopLite.Api.Tests.Infrastructure;

public static class TestUsers
{
    public static readonly (string Username, string Password) Alice = ("alice", "Alice123!");
    public static readonly (string Username, string Password) Bob = ("bob", "Bob123!");
    public static readonly (string Username, string Password) Admin = ("admin", "Admin123!");
}

public sealed record TokenResponse(string AccessToken, DateTimeOffset ExpiresAt, string Username, string Role);

public static class HttpClientExtensions
{
    public static async Task<HttpClient> CreateAuthenticatedClientAsync(
        this ShopLiteApiFactory factory,
        (string Username, string Password) user)
    {
        var client = factory.CreateClient();
        var response = await client.PostAsJsonAsync("/api/auth/login", new { username = user.Username, password = user.Password });
        response.EnsureSuccessStatusCode();
        var token = await response.Content.ReadFromJsonAsync<TokenResponse>();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token!.AccessToken);
        return client;
    }

    public static HttpClient WithLanguage(this HttpClient client, string language)
    {
        client.DefaultRequestHeaders.AcceptLanguage.Clear();
        client.DefaultRequestHeaders.AcceptLanguage.Add(new StringWithQualityHeaderValue(language));
        return client;
    }
}

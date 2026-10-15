namespace ShopLite.Api.Auth;

public sealed class JwtSettings
{
    public const string SigningKeyVariable = "SHOPLITE_JWT_KEY";
    public const int MinimumKeyLength = 32;

    public string Issuer { get; set; } = "shoplite";
    public string Audience { get; set; } = "shoplite-web";
    public int LifetimeMinutes { get; set; } = 120;
    public string SigningKey { get; set; } = string.Empty;
}

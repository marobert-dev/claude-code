using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;

namespace ShopLite.Api.Auth;

public static class AuthenticationSetup
{
    public static IServiceCollection AddShopLiteAuthentication(this IServiceCollection services)
    {
        services.AddOptions<JwtSettings>()
            .Configure<IConfiguration>((settings, configuration) =>
            {
                configuration.GetSection("Jwt").Bind(settings);
                settings.SigningKey = configuration[JwtSettings.SigningKeyVariable] ?? string.Empty;
            })
            .Validate(
                settings => settings.SigningKey.Length >= JwtSettings.MinimumKeyLength,
                $"{JwtSettings.SigningKeyVariable} must be set to a key of at least {JwtSettings.MinimumKeyLength} characters.")
            .ValidateOnStart();

        services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer();
        services.AddOptions<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme)
            .Configure<IOptions<JwtSettings>>((options, jwt) =>
            {
                options.MapInboundClaims = false;
                options.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidIssuer = jwt.Value.Issuer,
                    ValidAudience = jwt.Value.Audience,
                    IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwt.Value.SigningKey)),
                    NameClaimType = ShopLiteClaims.Name,
                    RoleClaimType = ShopLiteClaims.Role,
                };
            });

        services.AddAuthorization();
        services.AddSingleton<TokenService>();
        return services;
    }
}

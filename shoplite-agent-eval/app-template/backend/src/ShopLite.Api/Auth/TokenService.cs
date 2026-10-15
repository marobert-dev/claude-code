using System.Security.Claims;
using System.Text;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using ShopLite.Api.Domain;
using ShopLite.Api.Dtos;

namespace ShopLite.Api.Auth;

public sealed class TokenService(IOptions<JwtSettings> options, TimeProvider timeProvider)
{
    private readonly JwtSettings settings = options.Value;

    public LoginResponse CreateToken(AppUser user)
    {
        var expiresAt = timeProvider.GetUtcNow().AddMinutes(settings.LifetimeMinutes);
        var descriptor = new SecurityTokenDescriptor
        {
            Issuer = settings.Issuer,
            Audience = settings.Audience,
            Expires = expiresAt.UtcDateTime,
            Subject = new ClaimsIdentity(
            [
                new Claim(ShopLiteClaims.UserId, user.Id.ToString()),
                new Claim(ShopLiteClaims.Name, user.Username),
                new Claim(ShopLiteClaims.Role, user.Role),
            ]),
            SigningCredentials = new SigningCredentials(
                new SymmetricSecurityKey(Encoding.UTF8.GetBytes(settings.SigningKey)),
                SecurityAlgorithms.HmacSha256),
        };

        var token = new JsonWebTokenHandler().CreateToken(descriptor);
        return new LoginResponse(token, expiresAt, user.Username, user.Role);
    }
}

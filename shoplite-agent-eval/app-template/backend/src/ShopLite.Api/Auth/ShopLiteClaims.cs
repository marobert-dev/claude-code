using System.Security.Claims;

namespace ShopLite.Api.Auth;

public static class ShopLiteClaims
{
    public const string UserId = "sub";
    public const string Name = "name";
    public const string Role = "role";

    public static int GetUserId(this ClaimsPrincipal principal) =>
        int.Parse(principal.FindFirstValue(UserId)
            ?? throw new InvalidOperationException("Authenticated principal has no user id claim."));
}

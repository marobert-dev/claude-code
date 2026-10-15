using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using ShopLite.Api.Auth;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;
using ShopLite.Api.Dtos;
using ShopLite.Api.Errors;

namespace ShopLite.Api.Services;

public class AuthService(ShopLiteDbContext db, IPasswordHasher<AppUser> hasher, TokenService tokenService)
{
    public async Task<LoginResponse> LoginAsync(LoginRequest request, CancellationToken ct)
    {
        var user = await db.Users.AsNoTracking().FirstOrDefaultAsync(u => u.Username == request.Username, ct);
        if (user is null || hasher.VerifyHashedPassword(user, user.PasswordHash, request.Password) == PasswordVerificationResult.Failed)
        {
            throw new InvalidCredentialsException();
        }

        return tokenService.CreateToken(user);
    }
}

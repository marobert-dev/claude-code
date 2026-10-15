using System.ComponentModel.DataAnnotations;

namespace ShopLite.Api.Dtos;

public sealed class LoginRequest
{
    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(50, ErrorMessage = "Validation.StringLength")]
    public string Username { get; init; } = string.Empty;

    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(100, ErrorMessage = "Validation.StringLength")]
    public string Password { get; init; } = string.Empty;
}

public sealed record LoginResponse(string AccessToken, DateTimeOffset ExpiresAt, string Username, string Role);

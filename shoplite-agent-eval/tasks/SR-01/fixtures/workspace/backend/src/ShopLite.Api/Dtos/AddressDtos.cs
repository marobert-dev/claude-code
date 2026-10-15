using System.ComponentModel.DataAnnotations;

namespace ShopLite.Api.Dtos;

public sealed class AddressRequest
{
    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(40, ErrorMessage = "Validation.StringLength")]
    public string Label { get; init; } = string.Empty;

    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(120, ErrorMessage = "Validation.StringLength")]
    public string Line1 { get; init; } = string.Empty;

    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(80, ErrorMessage = "Validation.StringLength")]
    public string City { get; init; } = string.Empty;

    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(12, ErrorMessage = "Validation.StringLength")]
    public string PostalCode { get; init; } = string.Empty;

    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(2, MinimumLength = 2, ErrorMessage = "Validation.StringLength")]
    public string Country { get; init; } = string.Empty;
}

public sealed record AddressDto(int Id, string Label, string Line1, string City, string PostalCode, string Country);

using System.ComponentModel.DataAnnotations;

namespace ShopLite.Api.Dtos;

public sealed class ProductQuery
{
    public const int DefaultPageSize = 12;

    [StringLength(100, ErrorMessage = "Validation.StringLength")]
    public string? Search { get; init; }

    [StringLength(60, ErrorMessage = "Validation.StringLength")]
    public string? Category { get; init; }

    [Range(1, int.MaxValue, ErrorMessage = "Validation.Range")]
    public int Page { get; init; } = 1;

    public int PageSize { get; init; } = DefaultPageSize;
}

public sealed record PagedResult<T>(IReadOnlyList<T> Items, int Page, int PageSize, int TotalCount, int TotalPages);

public sealed record ProductSummaryDto(int Id, string Name, string Category, decimal Price, bool InStock);

public sealed record ProductDto(int Id, string Name, string Description, string Category, decimal Price, int Stock);

public sealed class ProductUpsertRequest
{
    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(120, ErrorMessage = "Validation.StringLength")]
    public string Name { get; init; } = string.Empty;

    [StringLength(1000, ErrorMessage = "Validation.StringLength")]
    public string Description { get; init; } = string.Empty;

    [Required(ErrorMessage = "Validation.Required")]
    [StringLength(60, ErrorMessage = "Validation.StringLength")]
    public string Category { get; init; } = string.Empty;

    [Range(typeof(decimal), "0.01", "100000", ParseLimitsInInvariantCulture = true, ErrorMessage = "Validation.Range")]
    public decimal Price { get; init; }

    [Range(0, 100000, ErrorMessage = "Validation.Range")]
    public int Stock { get; init; }
}

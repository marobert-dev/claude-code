using System.ComponentModel.DataAnnotations;

namespace ShopLite.Api.Dtos;

public sealed class AddCartItemRequest
{
    [Range(1, int.MaxValue, ErrorMessage = "Validation.Range")]
    public int ProductId { get; init; }

    public int Quantity { get; init; } = 1;

    public decimal? UnitPrice { get; init; }
}

public sealed class UpdateCartItemRequest
{
    public int Quantity { get; init; }
}

public sealed record CartItemDto(int Id, int ProductId, string ProductName, decimal UnitPrice, int Quantity);

public sealed record CartDto(IReadOnlyList<CartItemDto> Items);

public sealed record CartSummaryDto(int Count, decimal Total);

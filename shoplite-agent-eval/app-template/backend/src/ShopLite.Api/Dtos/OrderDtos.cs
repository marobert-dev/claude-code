namespace ShopLite.Api.Dtos;

public sealed record OrderLineDto(int ProductId, string ProductName, int Quantity, decimal UnitPrice, decimal LineTotal);

public sealed record OrderDto(
    int Id,
    string Number,
    DateTime CreatedAtUtc,
    decimal Subtotal,
    decimal Discount,
    decimal Total,
    IReadOnlyList<OrderLineDto> Lines);

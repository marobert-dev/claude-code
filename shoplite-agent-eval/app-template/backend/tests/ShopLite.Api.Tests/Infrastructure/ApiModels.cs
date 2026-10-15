namespace ShopLite.Api.Tests.Infrastructure;

public sealed record ProductSummary(int Id, string Name, string Category, decimal Price, bool InStock);

public sealed record Product(int Id, string Name, string Description, string Category, decimal Price, int Stock);

public sealed record PagedProducts(List<ProductSummary> Items, int Page, int PageSize, int TotalCount, int TotalPages);

public sealed record CartItem(int Id, int ProductId, string ProductName, decimal UnitPrice, int Quantity);

public sealed record Cart(List<CartItem> Items);

public sealed record OrderLine(int ProductId, string ProductName, int Quantity, decimal UnitPrice, decimal LineTotal);

public sealed record Order(int Id, string Number, DateTime CreatedAtUtc, decimal Subtotal, decimal Discount, decimal Total, List<OrderLine> Lines);

public sealed record Problem(int? Status, string? Title, string? Detail, Dictionary<string, string[]>? Errors);

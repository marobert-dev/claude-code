namespace ShopLite.Api.Domain;

public class Product
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public string Description { get; set; } = string.Empty;
    public required string Category { get; set; }
    public decimal Price { get; set; }
    public int Stock { get; set; }
}

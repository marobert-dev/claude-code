namespace ShopLite.Api.Domain;

public class Order
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public required string Number { get; set; }
    public DateTime CreatedAtUtc { get; set; }
    public decimal Subtotal { get; set; }
    public decimal Discount { get; set; }
    public decimal Total { get; set; }
    public List<OrderLine> Lines { get; set; } = [];
}

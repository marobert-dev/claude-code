using System.Globalization;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Localization;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;
using ShopLite.Api.Dtos;
using ShopLite.Api.Errors;

namespace ShopLite.Api.Services;

public class OrderService(
    ShopLiteDbContext db,
    IStringLocalizer<SharedResource> localizer,
    TimeProvider timeProvider,
    ILogger<OrderService> logger)
{
    private const string OrderNumberPrefix = "SL-";
    private const string OrderNumberFormat = "D6";
    private const string ReceiptDateFormat = "yyyy-MM-dd";
    private const string MoneyFormat = "0.00";
    private const string CurrencySuffix = " €";
    private const decimal MediumOrderThreshold = 100m;
    private const decimal LargeOrderThreshold = 200m;
    private const decimal MediumOrderDiscountRate = 0.05m;
    private const decimal LargeOrderDiscountRate = 0.10m;

    public async Task<OrderDto> CheckoutAsync(int userId, CancellationToken ct)
    {
        var cartItems = await db.CartItems
            .Include(i => i.Product)
            .Where(i => i.UserId == userId)
            .OrderBy(i => i.Id)
            .ToListAsync(ct);

        if (cartItems.Count == 0)
        {
            throw new BusinessRuleException("Error.EmptyCart");
        }

        var subtotal = RoundMoney(cartItems.Sum(i => i.UnitPrice * i.Quantity));
        var discount = CalculateDiscount(subtotal);
        var order = new Order
        {
            UserId = userId,
            Number = await NextOrderNumberAsync(ct),
            CreatedAtUtc = timeProvider.GetUtcNow().UtcDateTime,
            Subtotal = subtotal,
            Discount = discount,
            Total = subtotal - discount,
        };
        db.Orders.Add(order);
        await db.SaveChangesAsync(ct);

        foreach (var item in cartItems)
        {
            db.OrderLines.Add(new OrderLine
            {
                OrderId = order.Id,
                ProductId = item.ProductId,
                Quantity = item.Quantity,
                UnitPrice = item.UnitPrice,
            });
            await db.SaveChangesAsync(ct);
        }

        db.CartItems.RemoveRange(cartItems);
        await db.SaveChangesAsync(ct);

        logger.LogInformation("Order {OrderNumber} created for user {UserId} ({LineCount} lines)", order.Number, userId, order.Lines.Count);

        var productNames = cartItems.ToDictionary(i => i.ProductId, i => i.Product!.Name);
        return ToDto(order, productNames);
    }

    public async Task<IReadOnlyList<OrderDto>> GetOrdersAsync(int userId, CancellationToken ct)
    {
        var orders = await db.Orders
            .Where(o => o.UserId == userId)
            .OrderByDescending(o => o.CreatedAtUtc)
            .ThenByDescending(o => o.Id)
            .ToListAsync(ct);

        var result = new List<OrderDto>();
        foreach (var order in orders)
        {
            var lines = await db.OrderLines.Where(l => l.OrderId == order.Id).OrderBy(l => l.Id).ToListAsync(ct);
            var productNames = new Dictionary<int, string>();
            foreach (var line in lines)
            {
                var product = await db.Products.FirstAsync(p => p.Id == line.ProductId, ct);
                productNames[product.Id] = product.Name;
            }

            result.Add(ToDto(order, productNames));
        }

        return result;
    }

    public async Task<OrderDto> GetOrderAsync(int userId, int orderId, CancellationToken ct)
    {
        var order = await db.Orders.AsNoTracking()
            .Include(o => o.Lines)
            .ThenInclude(l => l.Product)
            .FirstOrDefaultAsync(o => o.Id == orderId, ct)
            ?? throw new NotFoundException("Error.OrderNotFound", orderId);

        var productNames = order.Lines
            .Where(l => l.Product is not null)
            .DistinctBy(l => l.ProductId)
            .ToDictionary(l => l.ProductId, l => l.Product!.Name);
        return ToDto(order, productNames);
    }

    public async Task<string> GetReceiptAsync(int userId, int orderId, CultureInfo culture, CancellationToken ct)
    {
        var order = await GetOrderAsync(userId, orderId, ct);
        return FormatReceipt(order, culture);
    }

    private static decimal CalculateDiscount(decimal subtotal)
    {
        var rate = subtotal switch
        {
            >= LargeOrderThreshold => LargeOrderDiscountRate,
            >= MediumOrderThreshold => MediumOrderDiscountRate,
            _ => 0m,
        };
        return RoundMoney(subtotal * rate);
    }

    private static decimal RoundMoney(decimal amount) => Math.Round(amount, 2, MidpointRounding.AwayFromZero);

    private async Task<string> NextOrderNumberAsync(CancellationToken ct)
    {
        var existingOrders = await db.Orders.CountAsync(ct);
        return OrderNumberPrefix + (existingOrders + 1).ToString(OrderNumberFormat, CultureInfo.InvariantCulture);
    }

    private static OrderDto ToDto(Order order, IReadOnlyDictionary<int, string> productNames) => new(
        order.Id,
        order.Number,
        order.CreatedAtUtc,
        order.Subtotal,
        order.Discount,
        order.Total,
        order.Lines
            .OrderBy(l => l.Id)
            .Select(l => new OrderLineDto(
                l.ProductId,
                productNames.GetValueOrDefault(l.ProductId, string.Empty),
                l.Quantity,
                l.UnitPrice,
                l.UnitPrice * l.Quantity))
            .ToList(),
        order.CancelledAtUtc);

    private string FormatReceipt(OrderDto order, CultureInfo culture)
    {
        var previousCulture = CultureInfo.CurrentUICulture;
        CultureInfo.CurrentUICulture = culture;
        try
        {
            var receipt = new StringBuilder();
            receipt.AppendLine(localizer["Receipt.Header", order.Number]);
            receipt.AppendLine(localizer["Receipt.Date", order.CreatedAtUtc.ToString(ReceiptDateFormat, CultureInfo.InvariantCulture)]);
            foreach (var line in order.Lines)
            {
                receipt.AppendLine(string.Format(
                    CultureInfo.InvariantCulture,
                    "{0} x {1} @ {2} = {3}",
                    line.Quantity,
                    line.ProductName,
                    FormatMoney(line.UnitPrice, culture),
                    FormatMoney(line.LineTotal, culture)));
            }

            receipt.AppendLine(localizer["Receipt.Subtotal", FormatMoney(order.Subtotal, culture)]);
            receipt.AppendLine(localizer["Receipt.Discount", FormatMoney(order.Discount, culture)]);
            receipt.Append(localizer["Receipt.Total", FormatMoney(order.Total, culture)]);
            return receipt.ToString();
        }
        finally
        {
            CultureInfo.CurrentUICulture = previousCulture;
        }
    }

    private static string FormatMoney(decimal amount, CultureInfo culture) =>
        amount.ToString(MoneyFormat, culture) + CurrencySuffix;
}

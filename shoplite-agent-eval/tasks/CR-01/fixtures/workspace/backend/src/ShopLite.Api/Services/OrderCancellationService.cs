using Microsoft.EntityFrameworkCore;
using ShopLite.Api.Data;
using ShopLite.Api.Dtos;
using ShopLite.Api.Errors;

namespace ShopLite.Api.Services;

public class OrderCancellationService(ShopLiteDbContext db, OrderService orderService, TimeProvider timeProvider)
{
    private const int CancellationWindowHours = 24;

    public async Task<OrderDto> CancelAsync(int userId, int orderId, CancellationToken ct)
    {
        var order = await db.Orders
            .Include(o => o.Lines)
            .ThenInclude(l => l.Product)
            .FirstOrDefaultAsync(o => o.Id == orderId, ct)
            ?? throw new NotFoundException("Error.OrderNotFound", orderId);

        if (order.CancelledAtUtc is not null)
        {
            throw new BusinessRuleException("Error.OrderAlreadyCancelled", order.Number);
        }

        var now = timeProvider.GetUtcNow().UtcDateTime;
        if (order.CreatedAtUtc > now.AddHours(-CancellationWindowHours))
        {
            throw new BusinessRuleException("Error.CancellationWindowClosed", CancellationWindowHours);
        }

        order.CancelledAtUtc = now;
        foreach (var line in order.Lines)
        {
            line.Product!.Stock += line.Quantity;
        }

        _ = db.SaveChangesAsync(ct);
        return await orderService.GetOrderAsync(userId, orderId, ct);
    }
}

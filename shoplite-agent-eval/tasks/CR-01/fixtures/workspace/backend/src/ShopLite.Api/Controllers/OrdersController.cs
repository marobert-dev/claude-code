using System.Globalization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ShopLite.Api.Auth;
using ShopLite.Api.Dtos;
using ShopLite.Api.Services;

namespace ShopLite.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/orders")]
public class OrdersController(OrderService orderService, OrderCancellationService cancellationService) : ControllerBase
{
    [HttpPost]
    [ProducesResponseType<OrderDto>(StatusCodes.Status201Created)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<OrderDto>> Checkout(CancellationToken ct)
    {
        var order = await orderService.CheckoutAsync(User.GetUserId(), ct);
        return CreatedAtAction(nameof(GetById), new { id = order.Id }, order);
    }

    [HttpGet]
    [ProducesResponseType<IReadOnlyList<OrderDto>>(StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<OrderDto>>> GetMine(CancellationToken ct) =>
        Ok(await orderService.GetOrdersAsync(User.GetUserId(), ct));

    [HttpGet("{id:int}")]
    [ProducesResponseType<OrderDto>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<OrderDto>> GetById(int id, CancellationToken ct) =>
        Ok(await orderService.GetOrderAsync(User.GetUserId(), id, ct));

    [HttpPost("{id:int}/cancel")]
    [ProducesResponseType<OrderDto>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status400BadRequest)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<OrderDto>> Cancel(int id, CancellationToken ct) =>
        Ok(await cancellationService.CancelAsync(User.GetUserId(), id, ct));

    [HttpGet("{id:int}/receipt")]
    [Produces("text/plain")]
    [ProducesResponseType<string>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetReceipt(int id, CancellationToken ct)
    {
        var receipt = await orderService.GetReceiptAsync(User.GetUserId(), id, CultureInfo.CurrentUICulture, ct);
        return Content(receipt, "text/plain; charset=utf-8");
    }
}

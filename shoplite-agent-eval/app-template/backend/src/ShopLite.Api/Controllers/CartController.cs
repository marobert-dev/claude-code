using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ShopLite.Api.Auth;
using ShopLite.Api.Dtos;
using ShopLite.Api.Services;

namespace ShopLite.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/cart")]
public class CartController(CartService cartService) : ControllerBase
{
    [HttpGet]
    [ProducesResponseType<CartDto>(StatusCodes.Status200OK)]
    public async Task<ActionResult<CartDto>> Get(CancellationToken ct) =>
        Ok(await cartService.GetCartAsync(User.GetUserId(), ct));

    [HttpPost("items")]
    [ProducesResponseType<CartDto>(StatusCodes.Status200OK)]
    [ProducesResponseType<ValidationProblemDetails>(StatusCodes.Status400BadRequest)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<CartDto>> AddItem(AddCartItemRequest request, CancellationToken ct) =>
        Ok(await cartService.AddItemAsync(User.GetUserId(), request, ct));

    [HttpPut("items/{itemId:int}")]
    [ProducesResponseType<CartDto>(StatusCodes.Status200OK)]
    [ProducesResponseType<ValidationProblemDetails>(StatusCodes.Status400BadRequest)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<CartDto>> UpdateItem(int itemId, UpdateCartItemRequest request, CancellationToken ct) =>
        Ok(await cartService.UpdateItemAsync(User.GetUserId(), itemId, request, ct));

    [HttpDelete("items/{itemId:int}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> RemoveItem(int itemId, CancellationToken ct)
    {
        await cartService.RemoveItemAsync(User.GetUserId(), itemId, ct);
        return NoContent();
    }
}

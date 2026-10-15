using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ShopLite.Api.Auth;
using ShopLite.Api.Dtos;
using ShopLite.Api.Services;

namespace ShopLite.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/addresses")]
public class AddressesController(AddressService addressService) : ControllerBase
{
    [HttpGet]
    [ProducesResponseType<IReadOnlyList<AddressDto>>(StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<AddressDto>>> List(CancellationToken ct) =>
        Ok(await addressService.ListAsync(User.GetUserId(), ct));

    [HttpGet("{id:int}")]
    [ProducesResponseType<AddressDto>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<AddressDto>> Get(int id, CancellationToken ct) =>
        Ok(await addressService.GetAsync(User.GetUserId(), id, ct));

    [HttpPost]
    [ProducesResponseType<AddressDto>(StatusCodes.Status201Created)]
    [ProducesResponseType<ValidationProblemDetails>(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<AddressDto>> Create(AddressRequest request, CancellationToken ct)
    {
        var address = await addressService.CreateAsync(User.GetUserId(), request, ct);
        return CreatedAtAction(nameof(Get), new { id = address.Id }, address);
    }

    [HttpPut("{id:int}")]
    [ProducesResponseType<AddressDto>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<AddressDto>> Update(int id, AddressRequest request, CancellationToken ct) =>
        Ok(await addressService.UpdateAsync(User.GetUserId(), id, request, ct));
}

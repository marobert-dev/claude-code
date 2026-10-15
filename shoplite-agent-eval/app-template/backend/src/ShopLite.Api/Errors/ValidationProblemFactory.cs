using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Localization;

namespace ShopLite.Api.Errors;

public static class ValidationProblemFactory
{
    public static IActionResult Create(ActionContext context)
    {
        var localizer = context.HttpContext.RequestServices.GetRequiredService<IStringLocalizer<SharedResource>>();
        var problem = new ValidationProblemDetails(context.ModelState)
        {
            Status = StatusCodes.Status400BadRequest,
            Title = localizer["Error.Validation.Title"],
        };
        return new BadRequestObjectResult(problem) { ContentTypes = { "application/problem+json" } };
    }
}

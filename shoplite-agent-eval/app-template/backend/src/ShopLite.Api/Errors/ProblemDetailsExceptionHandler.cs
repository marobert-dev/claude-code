using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Localization;

namespace ShopLite.Api.Errors;

public sealed class ProblemDetailsExceptionHandler(
    IProblemDetailsService problemDetailsService,
    IStringLocalizer<SharedResource> localizer,
    ILogger<ProblemDetailsExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        var problem = exception is AppException appException
            ? FromAppException(appException)
            : FromUnexpectedException(exception);

        httpContext.Response.StatusCode = problem.Status ?? StatusCodes.Status500InternalServerError;
        return await problemDetailsService.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = httpContext,
            ProblemDetails = problem,
            Exception = exception,
        });
    }

    private ProblemDetails FromAppException(AppException exception) => new()
    {
        Status = exception.StatusCode,
        Title = localizer[exception.TitleKey],
        Detail = localizer[exception.DetailKey, exception.DetailArgs],
    };

    private ProblemDetails FromUnexpectedException(Exception exception)
    {
        logger.LogError(exception, "Unhandled exception while processing the request");
        return new ProblemDetails
        {
            Status = StatusCodes.Status500InternalServerError,
            Title = localizer["Error.Unexpected.Title"],
            Detail = exception.Message,
            Extensions = { ["exception"] = exception.ToString() },
        };
    }
}

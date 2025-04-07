from doctest import debug
import logging
import stripe

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.payment import payment_router
from src.config import env, scheduler, pb, init_logger

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    init_logger()
    logger.info("Starting the app")

    await pb.login()
    scheduler.start()

    stripe.api_key = env.stripe_api_key

    yield

    # SHUTDOWN
    await pb.close()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(payment_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(stripe.error.StripeError)
async def stripe_error_handler(request: Request, exc: stripe.error.StripeError):
    logger.error(f"[Stripe] error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "[Stripe]: Unexpected payment processing error. Please try again or contact support."
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=env.env == "local")

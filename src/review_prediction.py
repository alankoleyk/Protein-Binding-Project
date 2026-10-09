"""Console walkthrough of the real presenter, with manually completed tasks.

Run from the repository root: python src/review_prediction.py
"""

from collections import deque

from adapters.demo import DemoBackend
from contracts import ViewState
from presenter import MainPresenter


class ConsoleView:
    def render(self, state: ViewState):
        self.state = state

    def show(self, revision, pending):
        state = self.state
        result = state.prediction
        prediction = f"{result.request.label}: {result.predicted}" if result else "none"
        print(f"  input={state.request.label} | revision={revision} | busy={state.busy}")
        print(f"  prediction={prediction} | error={state.error!r} | pending={pending}")


class ManualTasks:
    """Hold callbacks until the walkthrough completes the next task in submission order."""

    def __init__(self):
        self.pending = deque()

    def submit(self, work, succeeded, failed):
        self.pending.append((work, succeeded, failed))

    def finish_next(self, error=None):
        work, succeeded, failed = self.pending.popleft()
        if error is not None:
            print(f"  task failed: {error}")
            failed(error)
        else:
            result = work()
            print(f"  task returned: {result.request.label}: {result.predicted}")
            succeeded(result)


def run_scenario(title, old_error=None):
    print(f"\n=== {title} ===")
    view = ConsoleView()
    tasks = ManualTasks()
    presenter = MainPresenter(view, DemoBackend(), tasks)

    def step(description, action):
        print(f"\n{description}")
        action()
        # Read the real revision for review visibility; only the presenter changes it.
        view.show(presenter._revision, len(tasks.pending))

    step("0. Initial state", presenter.start)
    step("1. Submit request A (D39A)", presenter.predict)
    step("2. Click Predict again without changing input", presenter.predict)
    step("3. Change input to B (D39N)", lambda: presenter.set_replacement("N"))
    step("4. Submit request B", presenter.predict)
    step("5. Complete the old request A", lambda: tasks.finish_next(old_error))
    step("6. Complete the current request B", tasks.finish_next)


def main():
    print("Prediction review: real MainPresenter + DemoBackend + manual task completion.")
    print("No Qt or threads are started. Prediction numbers are invented demo values.")
    print("pending counts submitted tasks whose completion has not yet been delivered.")
    print("Each step prints the actual state last sent to the view.")
    run_scenario("Scenario 1: the old request succeeds")
    run_scenario("Scenario 2: the old request fails", old_error="Simulated failure for request A")
    print("\nReview checkpoints (expected behavior, not automated assertions):")
    print("  Step 2: pending stays at 1; the duplicate click is ignored.")
    print("  Step 3: busy=False while pending=1; changing input does not cancel old work.")
    print("  Step 5: input=D39N, busy=True, prediction=none, error=''.")
    print("  Step 6: input=D39N, busy=False, prediction=D39N: 1.65, error='', pending=0.")


if __name__ == "__main__":
    main()

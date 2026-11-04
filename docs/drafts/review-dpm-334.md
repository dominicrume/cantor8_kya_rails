Review-On: https://github.com/digital-asset/dpm/pull/334
How: Files changed tab > Review changes > "Comment" > Submit review.
     NOT the comment box at the bottom of the Conversation tab. Only the
     Files-changed route makes GitHub count you in reviewed-by:dominicrume.

Approve.

`os.Kill` is SIGKILL and can never be delivered to a handler, so
`signal.NotifyContext` was watching for something that could not arrive.
Nothing is lost by dropping it. The regression that fails against the old
entry point and passes against the new one is what makes this reviewable at
all, and the body is precise about reaping the *direct* component.

One question on the word "forward" in #190. `cmd.Cancel` is unset at
`pkg/assistant/assistant.go:265`, so `CommandContext` falls back to
`Process.Kill`, and the component is SIGKILLed rather than asked to stop. A
long-running component gets no chance to flush. Two lines would change it:

    cmd.Cancel = func() error { return cmd.Process.Signal(syscall.SIGTERM) }
    cmd.WaitDelay = 10 * time.Second

`TestMainCancelsComponentOnSignal` passes either way, since it asserts the
child disappears rather than how it was asked. Follow-up rather than this PR?

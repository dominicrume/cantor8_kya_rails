Review-On: https://github.com/digital-asset/dpm/pull/334
How: Files changed tab > Review changes > "Comment" > Submit review.
     NOT the comment box at the bottom of the Conversation tab. Only the
     Files-changed route makes GitHub count you in reviewed-by:dominicrume.

Approve.

`os.Kill` is SIGKILL, which can never be delivered to a handler, so listing it
in `signal.NotifyContext` could never have fired. Swapping it for
`syscall.SIGTERM` is the whole fix and it is the right one. The regression test
is what makes this reviewable at all: it drives the real binary, loops over
both SIGTERM and os.Interrupt, and puts the child in its own process group
with `Setpgid`, so a surviving grandchild is detectable rather than assumed.

One question on the word "forward" in #190. `cmd.Cancel` is unset at
`pkg/assistant/assistant.go:265`, so `CommandContext` falls back to
`Process.Kill`, and the component is SIGKILLed rather than asked to stop. A
long-running component gets no chance to flush. Two lines would change it:

    cmd.Cancel = func() error { return cmd.Process.Signal(syscall.SIGTERM) }
    cmd.WaitDelay = 10 * time.Second

`TestMainCancelsComponentOnSignal` passes either way, since it asserts the
child disappears rather than how it was asked. Follow-up rather than this PR?

; ModuleID = 'combined_optimized.c'
source_filename = "combined_optimized.c"

declare i32 @get_buffer_limit()

define void @process(ptr %buf, i32 %n) {
entry:
  %cmp = icmp sle i32 %n, 256
  br i1 %cmp, label %if.then, label %if.end

if.then:
  ret void

if.end:
  ret void
}

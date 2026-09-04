#pragma once

#include <condition_variable>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

class ThreadPool {
    std::vector<std::thread> workers_;
    std::mutex mu_;
    std::condition_variable cv_work_, cv_done_;
    std::function<void(int, int)> task_;
    int n_items_ = 0;
    int n_workers_;
    int finished_ = 0;
    uint64_t epoch_ = 0;
    uint64_t done_epoch_ = 0;
    bool stop_ = false;

    void worker_fn(int id) {
        uint64_t my_epoch = 0;
        while (true) {
            std::unique_lock lk(mu_);
            cv_work_.wait(lk, [&] { return epoch_ > my_epoch || stop_; });
            if (stop_) return;
            my_epoch = epoch_;
            int chunk = (n_items_ + n_workers_ - 1) / n_workers_;
            int lo = id * chunk;
            int hi = std::min(lo + chunk, n_items_);
            auto fn = task_;
            lk.unlock();

            if (lo < hi) fn(lo, hi);

            lk.lock();
            if (++finished_ == n_workers_) {
                done_epoch_ = my_epoch;
                cv_done_.notify_one();
            }
        }
    }

public:
    explicit ThreadPool(int n) : n_workers_(n) {
        for (int i = 0; i < n; ++i)
            workers_.emplace_back(&ThreadPool::worker_fn, this, i);
    }
    ~ThreadPool() {
        { std::lock_guard<std::mutex> lk(mu_); stop_ = true; }
        cv_work_.notify_all();
        for (auto& w : workers_) w.join();
    }
    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    void run(int n, std::function<void(int, int)> fn) {
        std::unique_lock<std::mutex> lk(mu_);
        task_ = std::move(fn);
        n_items_ = n;
        finished_ = 0;
        ++epoch_;
        lk.unlock();
        cv_work_.notify_all();
        lk.lock();
        cv_done_.wait(lk, [&] { return done_epoch_ == epoch_; });
    }
};
